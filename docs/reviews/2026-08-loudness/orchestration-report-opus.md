# Orchestration Report — Watcher/Loudness Integration Fix

**Status:** DELIVERED
**Date:** 2026-08-23
**Orchestrator/reviewer:** Claude Opus 5 (this runtime)
**Implementer:** Codex (`gpt-5.6-sol`), sibling terminal, same worktree
**Branch:** `FmBlueSystem/watcher-loudness-fix`
**Shipped to:** `origin/main` at `5f6d69e`

## Problem

Loudness tag writes emitted real filesystem events inside the watched library
folder. `LibraryWatchService` could not distinguish them from external edits, so
the app raised its "changes detected — rescan" affordance in response to writes
it had performed itself.

## Delivered commits

| Commit | Subject | Changed lines |
| --- | --- | --- |
| `07b28b4` | Merge branch 'main' into FmBlueSystem/watcher-loudness-fix | baseline sync |
| `5336e42` | fix(watcher): ignore bounded loudness tag events | 229 (+), 6 (-) |
| `8d3ef3d` | docs(watcher): document loudness event suppression | 189 (+), 17 (-) |
| `5f6d69e` | Merge branch 'FmBlueSystem/watcher-loudness-fix' (into main) | merge commit |

Combined: 19 files, 418 insertions, 23 deletions. Code-only (`src/`, `tests/`):
231 insertions, 6 deletions.

## Mechanism

- `LibraryWatchService.suppress_paths(paths, *, duration_seconds)` records
  canonical (`Path.resolve(strict=False)`) app-owned write paths against a
  monotonic expiry, under a `threading.Lock`.
- `_on_raw_event_main_thread` consults the map and returns early **before**
  arming the debounce timer — the only point where the event still carries path
  identity.
- Expired entries are purged lazily on each read/write; no timer, no cleanup
  thread.
- `LoudnessCompletionService` depends only on a narrow `PathChangeSuppressor`
  Protocol and registers its exact tag target immediately **before** invoking
  the tag writer. The audio layer holds no reference to desktop types.
- Suppression window: `_TAG_WRITE_SUPPRESSION_SECONDS = 5.0`, injectable per
  call via `duration_seconds`; the clock is injectable via `monotonic_clock`.

## Required scenarios — verified present

All three live in `tests/test_library_watch_service.py`, in
`test_loudness_tag_write_events_are_suppressed_but_external_changes_and_expiry_surface`,
which wires the real `LoudnessCompletionService` to the real
`LibraryWatchService` through a real `FolderWatcher`, with the tag writer firing
a genuine event:

1. **Loudness batch does not raise the affordance** — after `complete()`,
   `timers[0].start_calls == []` and `state.model_copy_calls == []`.
2. **External change still does** — firing an unrelated path settles the
   debounce and yields one `changes_detected_since_scan` transition.
3. **Suppression expires** — after `clock.advance(5.0)`, firing the *same*
   previously suppressed path yields a second transition.

Supporting: `test_completion_suppresses_the_exact_tag_target_before_writing`
asserts ordering (`[("suppress", [path]), ("write", None)]`), and
`test_window_factory_wires_one_watcher_to_scan_and_loudness_and_stops_it`
asserts single-instance composition and shutdown.

## Independent verification (run by the orchestrator, not trusted from Codex)

Branch tree `8d3ef3d`, full `AGENTS.md` recipe:

| Gate | Codex claimed | Orchestrator measured |
| --- | --- | --- |
| `uv run pytest -q` | 1855 passed | **1855 passed** (58.00s) |
| `uv run pyright src tests` | 0 errors | **0 errors, 0 warnings, 0 informations** |
| `uv run pytest --cov --cov-fail-under=70 -q` | 91.36% | **91.36%** |
| `uv run ruff check .` | clean | **All checks passed** |
| `uv run ruff format --check .` | 307 formatted | **307 already formatted** |
| `uv run python scripts/release_gate_check.py --run` | exit 0 | **exit 0** |

Every claimed figure reproduced exactly. No inflation found.

Post-merge on `main` at `5f6d69e`: `1855 passed` (70.14s), pyright
`0 errors`, `ruff check` clean, `ruff format --check` 307 files. Verdict:
`MERGED MAIN ALL GREEN`. The merged tree was additionally proven byte-identical
to the verified branch tree (`git diff --quiet 8d3ef3d 5f6d69e`).

## Decisions made by the orchestrator

1. **Merge topology.** The branch was 6 ahead / 0 behind `main`, so a
   fast-forward was available. Used `--no-ff` anyway to preserve an explicit,
   revertable integration point, per the conventional-merge requirement.
2. **Merge location.** `main` was checked out in no worktree
   (`~/Documents/xfinaudio-local-main` holds
   `feat/library-file-watcher-integration`). Created a disposable worktree at
   `../_merge-main` rather than hijacking another checkout.
3. **Post-merge verification scope.** Ran tests, pyright and both ruff gates on
   the merged tree. Did not re-run the coverage gate or the release gate there:
   the merged tree is provably identical to the branch tree where both had
   already passed, and re-running would have measured the environment, not the
   code.
4. **Accepted the 5-second suppression window** as shipped. It is a calibration
   knob, not a constant to argue about: macOS FSEvents delivery latency is well
   under it, and both the duration and the clock are injectable.

## Deviations from the original mandate

1. **Three scenarios, one test function.** The mandate asked for three
   integration tests; Codex delivered one narrative test asserting all three in
   sequence. Accepted: the expiry assertion depends on state established by the
   suppression assertion, so splitting would duplicate setup for no added
   coverage.
2. **Combined diff of 418 insertions exceeds the 400-line review budget.** Each
   individual commit is within budget (229 and 189), and only 231 lines are
   code — the remainder is `openspec/` SDD artifacts and documentation.
3. **Adjacent scope in `LibraryWatchService`.** `set_state()` and the
   `state_setter` accessor were added beyond pure suppression. They fix the
   watcher holding a stale private copy of `AppState` without propagating it
   back to the owner. Judged necessary for the affordance to reflect reality
   rather than scope creep, and it respects `AppState` immutability
   (`model_copy`).

## Known bounded behaviour

A genuine external edit to the *same* file during the 5-second window after an
app-owned write is swallowed. This is documented and intentional; a later edit
to that path is detected normally, and no path is ever suppressed permanently.

## Guardrails observed

- No force push. Push was a fast-forward `7ee0b72..5f6d69e`, verified with
  `git merge-base --is-ancestor` immediately after a fresh fetch.
- `main` only. No other branch was pushed.
- No AI attribution in any commit message.
- No `recommendation/` business logic touched. Rollback is `git revert 5336e42`.

## Cleanup

The disposable `../_merge-main` worktree was removed after the push.

## Disk freed

Free space on `/`: **6.5 GiB → 7.3 GiB** (net ≈ **800 MB** recovered).

### Deleted

| Path | `du -sh` size | Notes |
| --- | --- | --- |
| `~/orca/workspaces/xfinaudio-local-main/_merge-main` | ~1.6 G | Disposable merge worktree created by this orchestration; removed after push. |
| `~/Documents/xfinaudio-local-main/out/dist` | 648 M | PyInstaller staged `.app`. Git-ignored, nothing tracked under `out/`. |
| `~/Documents/xfinaudio-local-main/out/build` | 75 M | PyInstaller intermediates. Git-ignored. |
| `<this worktree>/.venv` | 1.6 G (**52 MB actually reclaimed**) | Deleted only after confirming `HEAD` is an ancestor of `origin/main`. |
| `<this worktree>/.pytest_cache` | 192 K | Disposable. |
| `<this worktree>/.ruff_cache` | 32 K | Disposable. |
| `<this worktree>/.coverage` | 104 K | Disposable. |

**APFS caveat — `du -sh` overstates reclaimable space here.** Removing a 1.6 G
`.venv` returned only 52 MB. `uv` materializes environments with `clonefile`,
so the venv's blocks are shared with `~/.cache/uv` and the sibling worktree's
`.venv`; `du` bills those shared blocks to every referrer. Judge venv cleanup
by `df` deltas, not by `du` totals.

### Not deleted — reported instead

| Path | Size | Why kept |
| --- | --- | --- |
| `~/.cache/uv` | 1.6 G | Shared cache. Per directive, removing it only slows future work. |
| `~/Documents/xfinaudio-local-main/.venv` | 1.6 G | Owner's primary checkout, currently on `feat/library-file-watcher-integration`. Active workspace, not this orchestration's to reclaim. |
| `~/Documents/xfinaudio-local-main/out/XfinAudio-1.8.2-loudness.dmg` | 140 M | Current release artifact. Never deleted. |
| `/private/tmp/pi-github-repos` | 85 M | Unrelated to this project and not named in the directive. |
| `/private/tmp/xfinaudio-wu4-ffmpeg-work`, `…-final-work` | 4 K each | Already emptied; deletion is not worth the risk surface. |

### RECOMMENDED-FOR-OWNER-DELETION

Pre-loudness release DMGs in the owner's main checkout, `~/Documents/xfinaudio-local-main/out/`
— **816 MB total**. These belong to the owner's checkout and were deliberately
left in place:

| File | Size |
| --- | --- |
| `XfinAudio-1.6.0.dmg` | 137 M |
| `XfinAudio-1.7.1.dmg` | 137 M |
| `XfinAudio-1.7.3.dmg` | 137 M |
| `XfinAudio-1.7.8.dmg` | 135 M |
| `XfinAudio-1.8.0.dmg` | 135 M |
| `XfinAudio-1.8.1.dmg` | 135 M |

Keep `XfinAudio-1.8.2-loudness.dmg` (140 M).

### `/tmp/ffmpeg-build-xfa` — measured, then vanished before deletion

Measured at **250 M** during the survey pass. By the time the deletion pass ran
minutes later it no longer existed, and the deletion helper reported it absent
without invoking `rm`. This orchestration did **not** delete it; the most
likely cause is macOS periodic `/tmp` cleanup. Its bundled-binary need was
already satisfied: `XfinAudio-1.8.2-loudness.dmg` was produced at 06:27, after
the FFmpeg build at 06:24–06:25, and embeds the validated universal binary.

### What remains in this worktree

This orchestration runs inside
`~/orca/workspaces/xfinaudio-local-main/watcher-loudness-fix`, so it cannot
remove its own worktree. For the owner:

- The branch `FmBlueSystem/watcher-loudness-fix` is fully contained in
  `origin/main` (`5f6d69e`), so the worktree is safe to remove with
  `git worktree remove <path>`.
- **Before removing it, copy `ORCHESTRATION-REPORT.md` out** — this file is
  untracked and lives only in that worktree.
