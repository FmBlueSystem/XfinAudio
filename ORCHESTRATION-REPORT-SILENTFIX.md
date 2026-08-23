# Orchestration report — silent loudness-stage skip

Date: 2026-08-23
Branch: `FmBlueSystem/loudness-silent-fix` → merged to `main` as `c73f66d`
Role: orchestrator + verifier (owner approved, autonomous)

## Symptom

In the installed frozen macOS app the loudness analysis stage was skipped entirely and
silently: the library scan completed, no loudness profile was ever written, and stderr
was empty.

## Root cause

`_supports_true_peak()` in `src/xfinaudio/audio/loudness.py` matched the ebur128 capability
probe with `^\s{5,}true\s+\d+\b`, requiring a numeric constant after the `true` enum row.

`peak` is an FFmpeg `<flags>` option, and FFmpeg prints the enum rows of a flags option
**without** a numeric constant:

```
   peak              <flags>      ..F.A...... set peak mode (default 0)
     true                         ..F.A...... enable true-peak mode
```

The predicate therefore returned `False` for every real FFmpeg build. `preflight()` raised
`FfmpegCapabilityError("Bundled FFmpeg ebur128 filter does not support true peak")`,
`create_loudness_completion_service()` swallowed it and returned `None`, `window_factory`
composed the window with no loudness service, and `LibraryController.start_loudness_completion`
early-returned on every scan. Six abort points, none of which produced any output.

A second, independent defect in the same probe pair: `_has_ebur128_filter()` required the
three-character filter-flag column of FFmpeg 7.x. FFmpeg 8 emits two, so the developer
path (PATH-resolved Homebrew FFmpeg 8.0.1) failed one step earlier — the stage had never
worked in development either, equally silently.

### Why it passed CI

Every preflight test fabricated the FFmpeg help output as `"  peak <int>\n     true 2"` —
declaring `peak` as `<int>` with a numeric constant. The fixtures encoded the same wrong
model of FFmpeg's output as the implementation, so the suite stayed green while the
product was broken.

## Evidence

Field evidence from the user's real installation:

| Column | Populated |
|---|---|
| `spectral_profile_json` | 10582 / 10582 |
| `danceability_profile_json` | 10582 / 10582 |
| `edge_spectral_profile_json` | 10527 / 10582 |
| `loudness_profile_json` | **0 / 10582** |

Every other completion stage populated fully; loudness was exactly zero. The
`loudness_profile_json` column existed, so this was not a missing migration.

Eliminated before reaching the root cause:

- Packaging: `/Applications/XfinAudio.app/Contents/Frameworks/ffmpeg` → `../Resources/ffmpeg`
  is a Mach-O universal arm64+x86_64 binary, runs, reports FFmpeg 7.1.1, exposes `ebur128`,
  carries no `com.apple.quarantine`, and passes `codesign --verify --deep --strict`.
- Settings: `~/.xfinaudio/settings.json` has `loudness.enabled = true`.

Reproduction against the shipped bundle, before the fix:

```
resolved: /Applications/XfinAudio.app/Contents/Resources/ffmpeg exists: True
fingerprint: ffmpeg-sha256:6443d958b8ec75cbd0c30ac9c9…
service: NONE -> SILENT SKIP
PREFLIGHT FAILED: FfmpegCapabilityError
MESSAGE: Bundled FFmpeg ebur128 filter does not support true peak
```

After the fix, against the same bundle and against PATH FFmpeg 8.0.1:

```
frozen service:  LoudnessCompletionService
dev/PATH service: LoudnessCompletionService
```

## Fix

`ff44d15 fix(loudness): accept real FFmpeg capability output in preflight`

- `_supports_true_peak()` accepts flag-style enum rows with no numeric constant, anchored
  to the trailing flags column so it still matches an option row rather than prose.
- `_has_ebur128_filter()` accepts a two- or three-character filter-flag column.
- Both probes are pinned to captured output from the bundled 7.1.1 build and from FFmpeg 8
  (`tests/fixtures/loudness/ffmpeg_*.txt`), replacing the fabricated strings.
- The capability gate stays real: a build whose ebur128 exposes no true-peak mode is still
  refused, with a regression test.

## Observability

`90629cf feat(loudness): make a skipped loudness stage visible`

The application configured **no logging at all**, so even an existing warning would have
been written nowhere in a Finder-launched `.app`. That is why the failure was silent
rather than merely obscure.

- Each of the three runtime composition aborts logs its own distinct reason, including the
  swallowed preflight exception text.
- `start_loudness_completion` distinguishes its three exits: engine unavailable and
  setting disabled are logged as skips; an active completion chain is logged as a
  deferral, since the chain restarts the stage when it drains.
- `configure_logging()` installs a rotating file handler at `~/.xfinaudio/xfinaudio.log`,
  called from `main()`, so those reasons survive where a bundled `.app` has no usable
  stderr.

End-to-end proof that a skip now leaves a trace:

```
2026-08-23 11:45:37,049 WARNING xfinaudio.audio.loudness_runtime:
Loudness analysis disabled: FFmpeg at …/ffmpeg did not report a usable version
```

Regression tests: the three runtime reasons must be distinct and non-empty; a scan that
skips the stage must log it; `configure_logging` must write to the file and must not
duplicate handlers on repeat startup.

## Verification

Run on merged `main` at `c73f66d`:

```
1862 passed, 45 warnings in 75.72s
pyright: 0 errors, 0 warnings, 0 informations
ruff check: All checks passed!
ruff format --check: 307 files already formatted
```

Baseline before the change was 1855 passed; the seven added tests account for the
difference. Slice sizes: 76 and 130 changed lines, both well under the 400-line budget.

## Decisions

1. **Delegation abandoned; orchestrator implemented.** The Cursor Grok worker in terminal
   `term_d9f7175f` never produced output. It entered a degenerate MCP tool-discovery loop,
   repeating "I'll inspect the installed app now and stop looping on tool discovery" while
   calling discovery tools, consumed ~130k tokens and 67% of its context in ~25 minutes,
   ignored a directive steer to use shell only, and then its process exited. Zero files
   touched, zero commits. The mandate's objective is to ship a verified fix, so the
   orchestrator took over implementation as maintainer rather than gamble another cycle on
   an environment-level failure mode that had already reproduced twice.
2. **FFmpeg 8 filter-column fix included.** Strictly it affects only the PATH-resolved
   developer path, not the frozen product. It is the same defect class in the same probe
   pair, discovered by the same evidence, and costs three characters plus a test. Leaving
   it would have shipped a known-broken predicate.
3. **Guard order in `start_loudness_completion` changed.** Now engine → setting → chain,
   so a durable reason is reported in preference to a transient one. Behaviour is
   unchanged — all three still return — and `settings_getter` is `lambda: window.settings`,
   an in-memory read.
4. **Logging installed after the package-smoke early return**, so the packaging smoke test
   does not create `~/.xfinaudio/`. No new environment override was added.
5. **Capability gate deliberately not weakened.** The probes were corrected, not relaxed
   into a fallback, per `design.md` §1, which requires the startup preflight to fail closed.

`design.md` §14 owner decisions were not revisited.

## Follow-up: a defect introduced by the observability change

`main()` called `configure_logging()` at the default path, so any test that called `main()`
installed a root handler pointing at the developer's own `~/.xfinaudio/xfinaudio.log`, and
every later test in the run appended to it. A full suite run left 438 lines of test noise
in a real user's log file.

Found by inspecting that log while trying to prove the frozen build had shipped the
observability — the log's contents were pytest paths, not application output, which also
showed the earlier "the frozen app wrote this" reading was wrong.

`db17c0a fix(desktop): keep the test suite out of the real log file` adds
`log_path_from_environment()` honoring `XFINAUDIO_LOG_PATH`, matching the existing
database and settings path overrides, and binds every `main()` test to `tmp_path`. A full
suite run now leaves the real log untouched.

## Delivery proof

The frozen build was verified by launching the installed app rather than by inference:

- `~/.xfinaudio/xfinaudio.log` was deleted, the installed `.app` was launched, and the
  file reappeared — so `configure_logging()` runs inside the frozen binary.
- The file was empty, so no `Loudness analysis disabled` line was written: the engine
  composed successfully. The pre-fix build would have written the true-peak rejection.

Build identity, `shasum -a 256` of `Contents/MacOS/XfinAudio`:

| Artifact | Hash prefix | Build |
|---|---|---|
| `~/Documents/xfinaudio-local-main/out/XfinAudio-1.8.2-loudness.dmg` (10:32) | `3ee97018…` | broken |
| `out/XfinAudio-1.8.2.dmg` (11:55) | `1a8a9f85…` | fixed, superseded |
| installed `/Applications/XfinAudio.app` | `813710cc…` | fixed, includes `db17c0a` |

The 10:32 DMG in `~/Documents` still installs the broken build and was left in place for
the owner to remove.

## Disk hygiene

See the closing summary for freed space and for the owner-deletion candidates, which were
listed but not executed.
