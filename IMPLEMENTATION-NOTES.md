# Implementation Notes

## add-loudness-module WU1a

- The minimum loudness duration is **3.0 seconds**. EBU R128 short-term loudness uses a
  3-second window, so this is the smallest duration at which LRA and true-peak values are
  retained by this module. Shorter material still preserves integrated LUFS and is typed
  `too_short` with LRA and dBTP unset.
- The golden fixture was captured from FFmpeg 8.0.1 against the synthetic 1 kHz WAV; the shipped bundle must use the same parser fixture or replace it when its pinned build is selected.
- `pyloudnorm` is a development-only conformance oracle. The runtime adapter remains the
  pinned FFmpeg command/parser boundary and never imports or invokes `pyloudnorm`.
- Process execution, preflight, timeout, cancellation, and orphan reaping remain WU1b.

## Autonomous blockers

### Native SDD runtime budget

The WU1 runtime objective is blocked at revision
`sha256:1e2e61ee5d3a9f086ab8b4ab5bc018f4a4bf2a0aa815c08caeb8aad288237aad`.
The native ledger counted 671 changed lines because the 354-line recovered binding contract
was committed after the WU1 objective was acquired, alongside the 327-line WU1a slice. Both
commits are independently below 400 lines, but native accounting correctly requires an
explicit maintainer reset before another apply or verification run. The autonomous mandate
does not authorize silently mutating that audit authority, so WU1b and WU2-WU4 were not
launched.

Required maintainer action:

```bash
gentle-ai sdd-attempt reset --cwd <repo> --change add-loudness-module \
  --expected-revision sha256:1e2e61ee5d3a9f086ab8b4ab5bc018f4a4bf2a0aa815c08caeb8aad288237aad \
  --request-id <unique-id> \
  --reason "Separate the recovered binding-contract import from the sub-400-line WU1 implementation slices" \
  --actor <maintainer>
```

### Audio-mutation governance

Before this reorder, WU3 tasks 3.3-3.5 required writing COMMENT and `XFINAUDIO_LOUDNESS`
tags while the root `AGENTS.md` made "No audio mutation" non-negotiable. WU4 task 4.6 was
scheduled after WU3, so the original order could not execute without violating active repository
instructions. Section 14 recorded product approval but did not amend the governance contract.
The maintainer-authorized task 4.6 reorder below resolves this ordering blocker before any WU3
write-back.

## Authorized Governance Reorder (WU4.6 before WU3)

The maintainer approved completing governance task 4.6 before any WU3 tag-write work.
`AGENTS.md`, `CONTRIBUTING.md`, and README English/Spanish now state that scanning remains
read-only and that the loudness module is the single documented exception, permitted to write
loudness tags only through its explicit setting. This authorizes the future WU3 boundary; it
does not implement or execute a tag write.


## add-loudness-module WU1b task 1.4

- Preflight requires an absolute executable file with execute permission, checks successful typed probe results, and parses the FFmpeg filter listing and `peak` option structurally rather than accepting unrelated words.
- The initial execution boundary remains shell-free with `stdin=DEVNULL`, `start_new_session=True`, and typed timeout failure. Process-group lifecycle safety follows in task 1.5.


## add-loudness-module WU1b task 1.5 correction

- `killpg` is followed by owner `communicate(timeout=None)`; a condition lock makes spawn/registration/cancel/unregister atomic and makes shutdown wait for each registered owner to reap.

## add-loudness-module WU1 self-verification at `202f6fc`

All requested WU1 verification gates passed on 2026-08-22 in the required order:

- `uv run pytest -q tests/audio/test_loudness.py` — 14 passed in 1.81s; wall 3.413s; output `sha256:7289061d73e890a291aae88043005e2f17f001fce8381fc6cc7840586dfca78c`.
- `uv run pytest -q` — 1706 passed, 266 warnings in 32.00s; wall 35.190s; output `sha256:ab3c020f50be511745b388161ef1084af6c3aa26ab2499ac23a6a58fc6a1e449`.
- `uv run pyright src tests` — 0 errors, 0 warnings, 0 informations; wall 5.244s; output `sha256:3c1a00ce86bcdce1ef7ba97d18d9c5b4e7026f49a5dc61a23382ed7345e02316`.
- `uv run ruff check .` — all checks passed; wall 0.115s; output `sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`.
- `uv run ruff format --check .` — 290 files already formatted; wall 0.054s; output `sha256:aed20c5cdfe9f925fe3d0e35cc2b37455ed39da2dab16a5441a0d6530c2e51af`.

Coverage and the release gate were intentionally not run. `uv run` caused only the known editable-project version drift in `uv.lock`; it was restored to HEAD. The untracked loudness review remained byte-identical, no source/tests changed, and root `build/`/`dist/` remained absent.

## Native ledger blocker after WU1 completion

WU1 is functionally complete and fully self-verified, but settlement of the WU1b objective
returned `maintainer_decision`. The original 303-line implementation required a fresh-context
gate correction for true reaping, synchronized cancellation, and strict capability probing.
That correction was committed separately at 399 lines, but the native objective accounts for
the combined final candidate and reports 560 changed lines against its 400-line limit.

Active ledger revision:
`sha256:d941ab0d243c9804d1f79fc3aa845bc725019a2f34af87a20dfcad2f139718c6`.

Required maintainer action before WU2:

```bash
gentle-ai sdd-attempt reset --cwd <repo> --change add-loudness-module \
  --expected-revision sha256:d941ab0d243c9804d1f79fc3aa845bc725019a2f34af87a20dfcad2f139718c6 \
  --request-id <unique-id> \
  --reason "Accept the separately committed sub-400-line WU1 preflight and lifecycle correction slices" \
  --actor <maintainer>
```

No WU2 actor or harness was launched after this native stop.


## add-loudness-module WU2a task 2.1

- `loudness_profile_json` follows the repository's nullable-column migration pattern: `_ensure_schema` adds it even when `PRAGMA user_version` already equals `SCHEMA_VERSION`. Therefore this additive column does **not** bump `SCHEMA_VERSION`.
- `save_scan_results` supplies `NULL` for the new column until later WU2 tasks own loudness writes/loads; its explicit `CASE` preserves an already-stored payload during ordinary metadata rescans.
- Maintainer budget: this task is constrained to 330 text changed lines including tests and artifacts, reserving correction margin.


## add-loudness-module WU2b tasks 2.2 and 2.4

- `load_loudness_profile_cache` validates the profile JSON, current analysis version, requested engine fingerprint, and the profile's own source mtime/size against a fresh file stat. It never reads shared `tracks.file_mtime_ns/file_size_bytes` for loudness validity.
- Typed statuses, including `transient_failure`, are returned from that cache for unchanged inputs so pipeline callers can avoid retry loops; `force_reanalyze=True` returns no cache entries.
- The supplied profile's post-write identity is serialized unchanged. Tag-write timing remains the caller's WU3 responsibility.

## add-loudness-module WU2c task 2.3

- `TrackRepository.refresh_post_metadata_identity` accepts only supported MP3/FLAC/WAV/AIFF suffixes, fresh-stats the existing path, and atomically updates only shared `file_mtime_ns` and `file_size_bytes`. It deliberately preserves the existing spectral, danceability, and edge JSON columns unchanged.
- It returns `False` before issuing SQL when `stat()` fails and is a post-tag-write boundary, not an arbitrary-audio-replacement API. WU3 remains responsible for ordering any tag write before this refresh.

## add-loudness-module WU2d task 2.5 core

- The headless completion core fixes its FFmpeg pool at **two workers**: native decode is external-drive I/O plus CPU work, so the existing CPU-derived worker count would cause avoidable disk contention.
- Until WU3 adds tag writing, each completed profile is fresh-stamped after analysis and persisted through `update_loudness_profile`; Qt/controller/runtime composition remains deliberately absent.

## add-loudness-module WU2e task 2.5 lifecycle

- A compact generic `BackgroundCompletionStage` replaces a copied fourth worker; it starts after edge completion, cancels with a new chain, and shuts down with the controller.
- Runtime composition remains deferred: `LibraryController` accepts the service injection, but no window-factory FFmpeg service is created before WU4.

## add-loudness-module WU2f task 2.5 runtime composition

- Runtime uses a SHA-256 fingerprint of successful shell-free `ffmpeg -version` output, so every exact build/configuration change invalidates the loudness cache.
- Frozen mode resolves only `<bundle>/ffmpeg`; developer PATH fallback is best-effort and unsupported binaries leave startup operational without loudness.

## add-loudness-module WU2 self-verification at `7a0a55e`

All requested gates passed on 2026-08-22: focused WU2 tests 112 passed in 3.01s (wall 3.963s, `sha256:249bc13b8c82a0b79aae798e1f3868613adecfa95cf919bf3f4ddc83fa7148e9`); full pytest 1729 passed with 261 warnings in 51.34s (wall 54.471s, `sha256:c590de63340a84073e06d55020ca65fbfdd421123a6ffe54e5aa630a8c5dd4cc`); Pyright reported 0 errors/warnings/informations (wall 5.087s, `sha256:3c1a00ce86bcdce1ef7ba97d18d9c5b4e7026f49a5dc61a23382ed7345e02316`); Ruff check passed (wall 0.104s, `sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`); Ruff format confirmed 296 files (wall 0.052s, `sha256:ba046a223e9f43762cca9c846332de658a26517c9939c3d67c012a2d214b899f`). Only transient `uv.lock` version drift occurred and was restored; the review doc stayed byte-identical, no source/tests changed, and root `build/`/`dist/` stayed absent.

## add-loudness-module WU3a tasks 3.1–3.2

- The immutable default band is **−10.0 LUFS ±2.0 LU**: a DJ-pool filter for modern mastered material, not streaming normalization or gain processing.
- `LoudnessBand` is an orthogonal argument with no loudness scoring weight; WU4 may persist an override without changing this strategy's semantics.


## add-loudness-module WU3b task 3.3

- The codec overwrites every ID3 `COMM` frame and writes `TXXX:XFINAUDIO_LOUDNESS`; FLAC uses Vorbis `COMMENT` and `XFINAUDIO_LOUDNESS`. MP3/WAV/AIFF are ID3-capable when tags can be created, while M4A and unknown suffixes return typed `unsupported`.
- It saves only changed complete `measured` values. WU3c must perform the post-write restat, shared identity refresh, and profile persistence.


## add-loudness-module WU3c task 3.4

- Fresh results always invoke the codec, then stamp profile-owned identity from a post-write stat. Only `changed` invokes `refresh_post_metadata_identity` before loudness persistence; cache replays never invoke the codec.
- A writer exception or unknown result is persisted as `transient_failure`; the service fresh-stats and refreshes siblings when that failed attempt changed identity.


## add-loudness-module WU3d task 3.5

- Recovery accepts only the exact v1 `lufs/lra/dbtp/v/engine` structured payload and never COMMENT or ReplayGain/R128. It fresh-stamps filesystem identity and FLAC MD5 when available.
- `save_scan_results` treats recovered values as bootstrap-only: it inserts them into NULL loudness rows but preserves any existing database profile.

## add-loudness-module WU3 self-verification at `f4bebe5`

After stale-count correction `b155d39`, lifecycle hardening `f4bebe5`, and termination of a separate 2h47m pytest process, the final exact gates passed: focused 386 tests (`sha256:8b672bcb479232a4d698d74b8f7ec5d7995db51abc38cc484ab5b6040b1d4717`), full 1762 tests with exit 0 (`sha256:e1fba8a18b6c073f9d8ffd3732ed083cd5f8dccf2a0d8ce9f590311213585723`), Pyright/Ruff/format green. Prior exit-134 teardown messages and later green runs establish sequence, not a proven thread root cause. Transient `uv.lock` drift was restored; review/source/tests/build/dist remained unchanged.

## add-loudness-module WU4a settings-model foundation

- `LoudnessSettings.enabled` controls whether a later WU4 wiring step schedules **new** loudness analysis. It is deliberately not a write-back preference: fresh measured profiles continue through the always-on, idempotent WU3 tag writer once analysis is scheduled.
- The persisted defaults reuse the strategy policy (`−10.0 LUFS`, `±2.0 LU`). Targets are constrained to `−30.0..0.0 LUFS` and tolerances to `0.0..10.0 LU`, preventing implausible settings while retaining exact-band and broad-library use cases.
- `CURRENT_SETTINGS_VERSION` remains `1`: the frozen AppSettings default factory lets existing v1 JSON without `loudness` load and deterministically round-trip the new defaults, while the existing hard future-version rejection remains unchanged.

## add-loudness-module WU4b settings UI and runtime wiring

- The settings dialog persists an immutable `LoudnessSettings` update. Its enabled flag blocks only new `LoudnessCompletionService` scheduling; cached/recovered profiles and target-band filtering remain available.
- A fresh enabled analysis still uses the existing always-on idempotent tag writer. There is deliberately no write-back preference or write-only mode.
- The current target/tolerance is forwarded through desktop recommendations and Prep Copilot into each strategy/prefilter boundary; default bands retain prior behavior until users change settings.

## add-loudness-module WU4c task 4.2

- Loudness completion owns immutable `is_completing_loudness`, count, and total fields. The stage initializes total from both cache-replay and fresh candidates; each active stage-scoped result increments only its own run, while stale/cancelled signals cannot mutate the current state.
- The library reuses its existing scan-progress label/bar with `Analyzing loudness {0:,}/{1:,}`. No table column or copied Qt worker is introduced; WU4.4 will localize the new source string.

## add-loudness-module WU4d task 4.3

- The library adds a selection-bound detail pane rather than a thirteenth table column. It reports one-decimal LUFS/LRA/dBTP only for complete measured profiles and explicitly reports missing, failed, unsupported, and too-short states.
- True-peak semantics are exact: `>= 0.0 dBTP` is clipping; `> -1.0 dBTP` and `< 0.0 dBTP` is warning; exactly `-1.0 dBTP` and lower has no badge. WU4.4 owns translations for the new source strings.

## add-loudness-module WU4e tasks 4.1 and 4.4

- Loudness strategy labels/descriptions use `BuildViewModel` translation calls; builder/mixin strings use the explicit `LibraryScreen` context so lupdate extracts and Qt resolves the same catalog keys.
- A full project lupdate revealed unrelated historical catalog churn. The committed catalogs retain only the twenty loudness entries per language, then regenerate both QM files from those TS sources.

## add-loudness-module WU4 final apply summary

- WU4 commits `067d078`–`f3f264c` establish validated settings, policy forwarding, immutable progress/detail UI, and translations. `6f8a781` separately authorizes the read-only governance exception. `a8a8cef`/`a574a42` add the pinned LGPL FFmpeg source/build, bundle contract, and provenance; `eb78a07`, `3d189cd`, `3c716c7`, and `179400d` close final lifecycle, coverage, lipo-order, and universal2 preservation defects.
- Final apply evidence: 1,802 tests passed; the exact coverage gate displayed 91.14% and met its 91.14% baseline; Pyright and Ruff were clean; the release gate passed with all checks. The real FFmpeg source build, PyInstaller temporary bundle, collected universal2 CLI capability validation, and package launch all passed.
- Build environment deviation: Homebrew NASM 3.02 supplied the required assembler; no opaque/prebuilt FFmpeg was used. PyInstaller reported 466 optional/platform missing-module warnings; they are recorded as non-blocking rather than suppressed.
- Native accounting treats all commits acquired in one objective as one combined candidate. Future work units must keep that combined additions-plus-deletions total below 400, including SDD evidence/docs while acquired.

## GATE REMEDIATION — WU2 verdict

- **W1 — fixed:** `src/xfinaudio/library/track_repository.py:32` now permits `.m4a` in the post-tag identity refresh; `tests/test_track_repository.py::test_refresh_post_metadata_identity_preserves_all_sibling_profiles_across_supported_formats` covers M4A alongside MP3/FLAC/WAV/AIFF and proves sibling caches remain valid.
- **W2 — fixed after running-path audit:** persisted display reads now select and deserialize `loudness_profile_json` (`track_repository.py:159-172,675-696`), so `window_factory.py:226-238` delivers it through `LibraryController.populate_track_table` (`library_controller.py:189-210`) into immutable state. Selection/result paths refresh the pane (`library_controller.py:262-269,753-761`); `library_screen_rendering.py:109-176` renders progress and measured LUFS/LRA/dBTP, while `translations/xfinaudio_{en,es}.ts:247-260` and `tests/test_loudness_translations.py` pin both catalogs.
- **W3 — fixed to user-reachable:** `track_repository.py:459-488` reuses unchanged typed failures but rejects stale analysis versions/fingerprints; the selected-track `Reanalyze loudness` detail action (`library_screen_builder.py`, `screens/library_screen.py`, `library_controller.py:744-750`) starts only the selected record with `force_reanalyze=True`, while automatic completion passes `False`. `tests/test_track_repository.py::test_loudness_cache_keeps_typed_failures_and_force_reanalyze_bypasses_them`, `::test_loudness_cache_rejects_malformed_or_stale_version_or_engine`, `tests/audio/test_loudness_completion.py::test_completion_force_reanalyze_bypasses_a_cached_transient_failure`, and `tests/test_loudness_completion_stage.py` prove reuse, invalidation, force retry, and disabled/no-op behavior.

## GATE N1 REMEDIATION

- The minimal LGPL FFmpeg surface now includes MOV demuxing plus AAC and ALAC decoding for existing M4A inputs. Source-build, PyInstaller pre-build, and post-bundle smoke probes fail closed unless all three capabilities are reported.
- Committed 3-second AAC-LC and ALAC M4A fixtures use the existing synthetic WAV with recorded commands and SHA-256 provenance in `tests/fixtures/loudness/README.md`; frozen-path coverage resolves the bundle-relative executable and executes a real decoder.
- Actual FFmpeg 7.1.1 universal2 build and PyInstaller collection passed with byte-identical SHA-256 `d17355d15b1dc107d7e8669a9e911b999fdfc86607432ee9e0941265d931a9aa`; both source and bundled adapters measured AAC-LC (`-20.0 LUFS`) and ALAC (`-20.0 LUFS`) fixtures through frozen resolution.
- **N1b:** M4A writes overwrite `©cmt` and the exact app-owned UTF-8 freeform atom while preserving unrelated atoms; scan coercion retains only that atom's native value for recovery, and non-UTF-8/binary/foreign values are rejected.
- **N1c:** `LoudnessCompletionService` gates each run with a synchronized cancellation/commit boundary: cancellation before commit skips writer, refresh, persistence, and result callbacks; cancellation during commit waits through write/restat/refresh/persist, then skips later commits. `tests/audio/test_loudness_completion.py` covers late analyzer return, blocked commit, and subsequent reuse.
- Final evidence for commits `e9e5802`, `a12dac8`, and `fc8972e`: focused N1 suite 82 passed; full suite 1,816 passed; coverage 91.27%; Pyright and Ruff passed; release gate passed. The actual rebuilt and bundled FFmpeg proof remains byte-identical at SHA-256 `d17355d15b1dc107d7e8669a9e911b999fdfc86607432ee9e0941265d931a9aa`.

## POST-MERGE DEBT FIXES

- **N2:** display reads now compare the persisted loudness profile's owned mtime/size with the scan-refreshed track identity. Replaced audio therefore renders as unmeasured until fresh analysis persists a matching profile; the stored JSON remains available to the existing cache/recovery lifecycle.
- **B9 residual:** `SECURITY.md` and every GitHub issue/PR template now state the same explicit loudness tag write-back exception already documented in `README.md`, `AGENTS.md`, and `CONTRIBUTING.md`; governance tests pin the wording across all surfaces.
- Verification: focused repository regression 11 passed; focused governance suite 11 passed; full suite 1,819 passed with 45 existing warnings; the final release gate reported 91.28% coverage; Pyright reported 0 errors/warnings/informations; Ruff check and format passed; the release gate passed.

## WATCHER-LOUDNESS INTEGRATION

- **Design:** `LibraryWatchService` keeps a lock-protected map of canonical
  exact paths with five-second monotonic expiry and checks it before debounce.
  `LoudnessCompletionService` receives the watcher only through a narrow
  suppressor protocol and registers the exact tag target before its writer.
- **Expiry:** no path is permanently ignored; stale entries are removed lazily.
  A different external path remains visible immediately; an external edit to
  the same path during the five-second interval is the intentional bounded
  ambiguity, and a later edit is detected normally.
- **TDD:** RED proved both missing seams; GREEN covers app-write suppression,
  unrelated external changes, expiry, exact target forwarding, composition,
  and shutdown.
- **Verification:** focused tests, full tests, Pyright, coverage, Ruff, and
  release gate evidence is recorded in this change's `verify-report.md`.
- **Runtime harness:** N/A. The deterministic fake watcher source and timer
  exercise the desktop event boundary without a real filesystem observer.
- **Rollback:** revert `5336e42` to remove only this cross-feature suppression
  and lifecycle wiring; no recommendation or business logic changes are part
  of the boundary.
