# Tasks

Status legend: `[ ]` not started, `[x]` done. Repository source of truth: `AGENTS.md`
(strict TDD, no audio mutation, no DSP, no live Serato V2 writes, immutable `AppState`,
pinned dependencies, 400-line review budget with an explicit chained-PR plan — see the
budget section of `proposal.md` and the measured per-unit review plan in `design.md` D10).

## W1 — Playlist export stays inside the export folder

- [x] Write the failing guard in `tests/test_playlist_file_export.py` for absolute names,
      separators, `..` and names that resolve outside the folder (RED).
- [x] Add `safe_target_name` and the resolved-parent containment check to
      `src/xfinaudio/exporting/playlist_file_export.py` (GREEN).
- [x] Confirm the focused file passes and the error text is the user-facing one.

## W2 — A staged AI request cannot change while its call is in flight

- [x] Write the failing renderer tests for a request staged during `pending === 'ask'`
      (RED).
- [x] Early-return in `setRequest` for the in-flight, non-editable, non-string and
      unchanged cases in `desktop-electron/renderer/optional-ai.ts` (GREEN).
- [x] Add the local-hold notice and the editable-state helper to
      `desktop-electron/renderer/optional-ai-view.ts`.
- [x] Re-run both renderer suites and rebuild the renderer bundle.

## W3 — Headless dependency snapshot matches the lock

- [x] Regenerate `desktop-electron/requirements-headless.txt` from `uv.lock` with
      `uv export --frozen` and delete the hand-edited `requirements-headless.in`.
- [x] Point `packaging/{linux,macos}/requirements-build.in` at the snapshot.
- [x] Write `tests/test_headless_requirements_lock_drift.py`: hash-locked pins, no
      unlocked distribution, version agreement with the lock.
- [x] Update `docs/third-party-license-inventory.md` and the macOS packaging README.
- [x] Regenerate `packaging/linux/requirements-build.txt` with
      `uv pip compile --generate-hashes --python-platform linux
      packaging/linux/requirements-build.in -o packaging/linux/requirements-build.txt`
      (exit 0): 37 pins, hash-locked, `packaging` 25.0, `setproctitle`/`watchdog`
      present, `cloudpickle` gone. The first attempt without `--python-platform linux`
      was rejected by inspection because it added the Darwin-only `macholib` pin to the
      Linux lock; the macOS file keeps that pin on top of the Linux include.
- [x] Extend `tests/test_headless_requirements_lock_drift.py` to guard the compiled
      lock itself (it previously guarded only the `.in` inputs): header command,
      every pin hash-locked, version agreement and completeness against the headless
      snapshot, and the macOS include. RED was demonstrated against the stale
      committed lock (`omits headless pins: ['setproctitle', 'watchdog']`) and with a
      temporary probe that stripped two `--hash` lines.

## W4 — Documents describe the tree that exists

- [x] Write `tests/test_documentation_freshness.py` (tracked documents, referenced paths,
      `uv run` targets, UI control names, historical banners, architecture registry).
- [x] Add `docs/architecture/README.md` and mark the superseded Qt-era notes historical.
- [x] Fix every reference the new guard found, one document at a time.
- [x] Reconcile `openspec/config.yaml` with `pyproject.toml` and `uv.lock`, and guard it in
      `tests/test_sdd_config_matches_project.py`.

## W5 — Discarded failures are observable

- [x] Write `tests/test_swallowed_exception_observability.py` (RED against the silent
      handlers).
- [x] Log a warning naming the track and the cause in `library/track_repository.py` and
      `library/scan_service.py` (GREEN).
- [x] Confirm the documented analyzer `None` contract in `audio/*.py` is left unchanged.

## W6 — SDD state and skill describe the live gate

- [x] Reconcile `openspec/changes/ai-playlist-improvement/state.yaml` with its own landed
      artifacts, without claiming approval.
- [x] Make `.atl/skills/gentle-ai-sdd-tdd/SKILL.md` gate-first and defer the coverage
      floor to `pyproject.toml`.
- [x] Guard the skill sequence in `tests/test_release_gate_check.py` (RED then GREEN).

## W7 — No Qt-era artifact ships, runs or is documented as current

- [x] Guard and then remove the Qt Linguist catalogs, their wheel force-include and the
      dead translation script config.
- [x] Remove `QT_QPA_PLATFORM: offscreen` from both workflows and guard it.
- [x] Guard and then reduce `src/xfinaudio/ai/connection_test.py` to the single probe
      literal, keeping `PROBE_MESSAGE` for its two live importers.
- [x] Rewrite `docs/ai-settings.md` with the labels the Electron panel ships and guard it.
- [x] Delete the untracked `src/xfinaudio/desktop/` bytecode tree.

## W8 — Improvement save is exercised against the real core

- [x] Add `desktop-electron/tests/editor-improvement.integration.test.mjs` driving the real
      bridge and Python core end to end, skipping when no interpreter is configured.
- [x] Prove the test is not vacuous with a temporary probe, then revert it.
- [x] Rebuild and run the suite with `XFIN_PYTHON`, and confirm the skip path without it.

## W9 — Durable record

- [x] `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `apply-progress.md` for this
      change (documentation only, no source change).
- [x] `verify-report.md` and `state.yaml` written from the W10 gate result.

## W10 — Verification

- [x] Run `uv run python scripts/release_gate_check.py --run --report-json
      /tmp/xfinaudio-release-gate-report.json` on this tree and record the result
      (`overall_status: passed`, nine gates, exit 0; two earlier runs found and fixed two
      guard/lint defects before this green run).
- [x] Regenerate `docs/release-candidate-evidence.md` from that report and re-run the
      documentation guards (70 passed; the stale `--cov-fail-under=70` row is gone).
- [x] Run the full Node suite with `XFIN_PYTHON` set and record pass/skip counts
      (519 passed, 0 failed, 0 skipped).
- [x] Launch the Electron app and confirm it starts against this tree (foreground GUI
      process, Chromium profile created, headless Python bridge spawned as its child; no
      screenshot, see `verify-report.md`), then close it.
- [x] Re-run the gate after the freezer-lock regeneration and record the new result; the
      lock change invalidates the earlier gate of record because it is a tracked file.
- [x] Land the work as local work-unit commits without pushing, tagging or merging, ordered
      so no commit is red: `W1` → `W2` → `W3` (locks + guards + the docs that describe them) →
      `W5` → `W7` → `W4` → `W6` → `W8` → `W9`+`W10` (this record and the regenerated
      evidence). The order is not the review order: the documentation-freshness guard (`W4`)
      only passes once the regenerated gate evidence and the Qt-era cleanup (`W7`) are in
      place, the SDD reconciliation (`W6`) asserts against the `pyproject.toml` that `W7`
      leaves behind, and `W6`'s release-gate guard reads the readiness document that `W4`
      rewrites. Each commit carries the test that proves its own fix, and the unit's focused
      tests were re-run after each commit.
- [x] Confirm nothing was pushed, tagged or merged; `origin/main` is untouched and the
      commits stay local to `feat/ai-playlist-improvement`.
