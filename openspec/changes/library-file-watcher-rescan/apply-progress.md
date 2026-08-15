# Apply Progress: Library File Watcher — Detect Changes, Prompt Rescan

## PR 1 of 2 (stacked-to-main): Tasks 1–8 — watcher abstraction + lifecycle service

Scope per Review Workload Forecast: watcher abstraction (`library/folder_watcher.py`)
+ desktop lifecycle service (`desktop/library_watch_service.py`) + their unit
tests. Both new modules are inert (dead code) at the end of this PR — nothing
in `scan_service.py`, `AppState`, or the Library screen UI references them
yet, so this slice is independently mergeable and safe to land alone.
PR 2 (Tasks 9–16) wires `scan_service.py`, `AppState`, and the UI affordance
on top of this PR.

## Completed tasks (Tasks 1–8)

- [x] **Task 1** — Pinned `"watchdog>=4.0,<7.0"` in `pyproject.toml`
  `[project].dependencies`; ran `uv lock` (resolved, added watchdog v6.0.0);
  confirmed `uv run pyright` project-wide stays at 0 errors with watchdog
  installed; confirmed `uv run pytest -q` still fully green before any
  behavior change.
- [x] **Task 2 (RED)** — Created `tests/test_folder_watcher.py` with
  `FakeEventSource` (records `start`/`stop`, exposes `fire()`) and 5 tests
  against `FolderWatcher`. Confirmed RED: `ModuleNotFoundError:
  xfinaudio.library.folder_watcher`.
- [x] **Task 3 (GREEN)** — Created `src/xfinaudio/library/folder_watcher.py`:
  `FileSystemEventSource` Protocol, `WatchdogEventSource` (wraps
  `watchdog.observers.Observer` + a `FileSystemEventHandler` subclass — the
  only module importing `watchdog` directly), `FolderWatcher`
  (`start`/`stop`/`is_watching`, no debounce). All 5 tests pass; `pyright`
  clean.
- [x] **Task 4 (REFACTOR)** — Reviewed naming/structure against
  `library/scan_service.py` conventions; no changes needed. Tests re-run
  green.
- [x] **Task 5 (RED)** — Created `tests/test_library_watch_service.py` with
  `FakeEventSource`, `FakeDebounceTimer` (`DebounceTimer` Protocol seam with
  synchronous `fire()`), and `FakeState` (records `model_copy(update=...)`
  calls). 11 tests covering start/debounce-restart/burst-coalesce/
  model_copy-on-timeout/pause/resume/pause-noop/resume-noop/stop-clears-
  pause/folder-switch, plus the cross-thread marshal test. Confirmed RED:
  `ModuleNotFoundError: xfinaudio.desktop.library_watch_service`.
- [x] **Task 6 (GREEN)** — Created
  `src/xfinaudio/desktop/library_watch_service.py`: `LibraryWatchService
  (QObject)` with `changes_detected` Signal, `start`/`stop`/`pause`/`resume`,
  internal `_raw_event_received = Signal(str)` cross-thread marshal, `@Slot
  (str) _on_raw_event_main_thread` that (re)starts the debounce timer,
  `_on_settle_timeout` that applies
  `state.model_copy(update={"changes_detected_since_scan": True})` before
  emitting `changes_detected` (only when state accessors are wired — see
  Deviation below), and `set_state_accessors(state=, sync_state=)` matching
  `ScanService`'s setter-injection pattern. Added the cross-thread marshal
  test using a plain `threading.Thread` + a `QApplication.processEvents()`
  pump loop (module-level `_APP` instance), matching the existing pattern in
  `tests/test_completion_worker_lifetimes.py` — `pytest-qt`/`qtbot` is not an
  installed dependency in this project, so the design doc's "qtbot/QSignalSpy"
  suggestion was adapted to the codebase's actual existing Qt-test convention.
  All 11 tests pass; `pyright` clean (0 errors).
- [x] **Task 7 (REFACTOR)** — Reviewed structural mirror against
  `desktop/scan_service.py` (setter-injection style, docstrings, section
  comments); no changes needed. Both test files re-run green together.
- [x] **Task 8 (VERIFY — PR 1 boundary)** — Ran the exact four scoped
  commands from tasks.md; all pass (see Verification Evidence below).

## Deviation from design.md

`design.md §3.1`'s `_on_settle_timeout` calls `self._sync_state()`
unconditionally, every time, regardless of whether `set_state_accessors` was
ever called (mirroring `ScanService`'s `_require_wired()`-gated pattern
elsewhere). Implemented instead as: only call `self._state.model_copy(...)`
and `self._sync_state()` when `self._state is not None` (i.e. when
`set_state_accessors` was called); `changes_detected` still emits
unconditionally either way. Rationale: `LibraryWatchService`, unlike
`ScanService`, has no `_require_wired()` guard method and no design-specified
requirement that `start()`/`pause()`/`resume()`/raw-event-handling need state
wiring — the design's own Testing Strategy table (§9) tests debounce/
coalesce/pause/resume against fake seams without necessarily wiring state
first. Un-conditioning the `_sync_state()` call would make
`LibraryWatchService` unusable in any test or composition-root ordering where
state accessors are wired after event handling could fire, and would crash
with `RuntimeError("... dependencies were not wired")` from the default
`_unwired` sentinel on the very first debounce timeout in any such case. This
is a defensive narrowing, not a behavior change relevant to the spec: in the
real wiring path (composition root always calls `set_state_accessors` before
`start()`), the observable behavior is identical to the design's literal
unconditional call.

## TDD Cycle Evidence

| Task | RED confirmed | GREEN confirmed | REFACTOR confirmed | Notes |
|------|----------------|------------------|----------------------|-------|
| 2/3/4 — `folder_watcher.py` | `ModuleNotFoundError` on `tests/test_folder_watcher.py` | 5/5 tests pass | 5/5 tests re-run pass, no prod change | |
| 5/6/7 — `library_watch_service.py` | `ModuleNotFoundError` on `tests/test_library_watch_service.py` | 11/11 tests pass | 16/16 (both files) re-run pass, no prod change | includes cross-thread marshal test |

## Files changed (this PR)

- `pyproject.toml` — +1 line (`watchdog>=4.0,<7.0` dependency)
- `uv.lock` — regenerated via `uv lock` (+31/-1, lockfile diff not counted
  against the human-review line budget per project convention)
- `src/xfinaudio/library/folder_watcher.py` — new, 83 lines
- `src/xfinaudio/desktop/library_watch_service.py` — new, 137 lines
- `tests/test_folder_watcher.py` — new, 83 lines
- `tests/test_library_watch_service.py` — new, 221 lines

**Real changed-line count (source-visible, excluding `uv.lock`):**
1 (pyproject.toml) + 83 + 137 + 83 + 221 = **525 lines**.

This exceeds the tasks.md line-estimate breakdown for this slice
(~200–240 lines) and the general 400-line review budget. The Review Workload
Guard already resolved `delivery_strategy: ask-on-risk` → chained PRs
confirmed by the user, and `chain_strategy: stacked-to-main`, before this
apply batch began, per the launch prompt. No further user prompt was raised
mid-apply since the chain boundary (Tasks 1–8 = PR 1) was already fixed by
tasks.md and the resolved delivery strategy; the actual line count is
reported here as a risk for the reviewer/orchestrator, not silently
absorbed. If the 525-line actual size is a concern, the natural further
split is `folder_watcher.py`+tests (166 lines) as its own PR ahead of
`library_watch_service.py`+tests (358 lines) — not attempted here since
tasks.md's stated PR 1 boundary (Task 8) explicitly groups both modules
together as "independently mergeable... inert... safe to land alone."

**Files explicitly NOT touched in this PR** (confirmed via `git diff`,
pre-existing uncommitted modifications from before this session, unrelated
to this change): `src/xfinaudio/recommendation/optimizer.py`,
`src/xfinaudio/recommendation/playlist_service.py`,
`tests/test_playlist_service.py`, `tests/test_sequence_optimizer.py`. Not
part of this PR's scope; left untouched.

**Also NOT touched (PR 2 scope, confirmed):** `scan_service.py`,
`app_state.py`, `library_screen_builder.py`, `screens/library_screen.py`,
`library_view_model.py`, `library_screen_rendering.py`.

## Verification Evidence

Scoped (Task 8, PR 1 boundary gate):

```
$ uv run pytest -q tests/test_folder_watcher.py tests/test_library_watch_service.py
16 passed

$ uv run pyright src/xfinaudio/library/folder_watcher.py \
    src/xfinaudio/desktop/library_watch_service.py \
    tests/test_folder_watcher.py tests/test_library_watch_service.py
0 errors, 0 warnings, 0 informations

$ uv run ruff check src/xfinaudio/library/folder_watcher.py \
    src/xfinaudio/desktop/library_watch_service.py
[] (0 findings)

$ uv run ruff format --check src/xfinaudio/library/folder_watcher.py \
    src/xfinaudio/desktop/library_watch_service.py
2 files already formatted
```

Full requested gates (per apply launch prompt, PR-1-of-2 slice — coverage
gate and `release_gate_check.py` explicitly skipped for this PR per launch
instructions, deferred to PR 2's Task 16 final gate):

```
$ uv run pytest -q
1717 passed, 255 warnings in 70.56s   → PASS (full suite, no regressions)

$ uv run pyright src tests
0 errors, 0 warnings, 0 informations   → PASS

$ uv run ruff check .
All checks passed!                     → PASS

$ uv run ruff format --check .
292 files already formatted            → PASS
```

## PR 2 of 2 (stacked-to-main): Tasks 9–16 — scan_service integration, AppState field, UI affordance, lifecycle edge cases — COMPLETE

- [x] **Task 9 (RED)** — `tests/test_scan_service.py`: added
      `FakeLibraryWatchService` spy + `set_watch_service()` injection tests
      (`test_begin_scan_state_pauses_watch_service_when_wired`,
      `test_end_scan_state_resumes_watch_service_when_wired`,
      `test_scan_service_works_without_watch_service_wired`, plus a coalescing
      integration test through the real `LibraryWatchService`). Confirmed RED
      before Task 10 landed.
- [x] **Task 10 (GREEN)** — `src/xfinaudio/desktop/scan_service.py`: added
      `_watch_service: LibraryWatchService | None` + `set_watch_service()`
      setter (setter-injection style, matching `set_state_accessors`/`set_ui`).
      `begin_scan_state()` calls `pause()`; `_end_scan_state()` calls
      `resume()`; `on_completed()`'s non-cancelled branch calls
      `watch_service.start(folder)` and clears
      `changes_detected_since_scan` via `model_copy(update=...)`
      unconditionally. All guarded by `is not None` — `ScanService` remains
      usable with no watch service wired.
- [x] **Task 11 (RED+GREEN)** — `tests/test_app_state.py`:
      `test_changes_detected_since_scan_default` asserts default `False`.
      `src/xfinaudio/desktop/app_state.py`: added
      `changes_detected_since_scan: bool = False` field.
- [x] **Task 12 (RED)** — `tests/test_library_view_model.py`:
      `test_rescan_button_visible_when_changes_detected_and_not_scanning`,
      `test_rescan_button_hidden_when_scanning_or_no_changes`.
      `tests/test_library_screen.py`: `test_rescan_button_hidden_by_default`,
      `test_rescan_button_visibility_follows_render`,
      `test_rescan_button_click_emits_rescan_requested`.
- [x] **Task 13 (GREEN)** — `library_screen_builder.py`: new
      `rescan_button` (`QPushButton`, `objectName="secondaryAction"`,
      `setVisible(False)` initial), added to the controls row.
      `screens/library_screen.py`: `rescan_requested = Signal()`, click wiring,
      tooltip/accessible-name entries, tab order after `cancel_button`, and
      `rescan_requested.connect(window.scan_selected_folder)` — the exact same
      target slot as the manual `scan_button`, per spec (no new scan path).
      `library_view_model.py`: `rescan_button_visible(state)` returns
      `state.changes_detected_since_scan and not state.is_scanning`.
      `library_screen_rendering.py`: `render()` sets `rescan_button`
      visibility from the view model.
- [x] **Task 14 (REFACTOR)** — Reviewed naming/structure against
      `scan_button`/`cancel_button` conventions; no changes needed.
- [x] **Task 15** — Lifecycle edge-case integration tests in
      `tests/test_library_watch_service.py`:
      `test_folder_switch_stops_old_watch_and_arms_new`,
      `test_shutdown_stops_watcher_with_no_leaked_threads`,
      `test_pause_during_scan_does_not_self_trigger_from_scan_reads`,
      `test_burst_across_pause_resume_debounce_chain_coalesces_once`; plus
      `test_pause_resume_debounce_burst_through_real_library_watch_service_coalesces_once`
      in `tests/test_scan_service.py`. No real-`watchdog`-against-temp-dir slow
      test was added — flagged as optional in design.md §9, not required for
      this change's acceptance criteria.
- [x] **Task 16 (VERIFY — final gate)** — see Verification Evidence below.

## Files changed (PR 2, this slice only)

- `src/xfinaudio/desktop/scan_service.py` — +15 lines (watch-service hooks)
- `src/xfinaudio/desktop/app_state.py` — +1 line (new field)
- `src/xfinaudio/desktop/library_screen_builder.py` — +4 lines (`rescan_button`)
- `src/xfinaudio/desktop/screens/library_screen.py` — +8/-1 lines (signal, wiring, tooltip, tab order)
- `src/xfinaudio/desktop/library_view_model.py` — +4 lines (`rescan_button_visible`)
- `src/xfinaudio/desktop/library_screen_rendering.py` — +1 line (render wiring)
- `tests/test_scan_service.py` — +184 lines
- `tests/test_app_state.py` — +3 lines
- `tests/test_library_view_model.py` — +21 lines
- `tests/test_library_screen.py` — +30 lines
- `tests/test_visual_integration.py` — +8 lines

**Real changed-line count (PR 2 alone):** 278 lines — within the 400-line
budget.

## Verification Evidence (PR 2 final gate, both PRs combined)

```
$ uv run pytest -q
1734 passed, 264 warnings

$ uv run pyright src tests
0 errors, 0 warnings, 0 informations

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
292 files already formatted

$ uv run pytest --cov --cov-fail-under=70 -q
1734 passed. Required test coverage of 70% reached. Total coverage: 91.03%

$ uv run python scripts/release_gate_check.py --run
All 19 individual gates PASS (tests/coverage, type-check, lint, format,
fixtures, DJ readiness, Serato dry-run, release readiness smoke,
publication/source-package hygiene, PyInstaller check-only, root artifact
hygiene). Exit code 0.
```

Note: one earlier `release_gate_check.py` run hit a nondeterministic exit 134
from a `QThread: Destroyed while thread '' is still running` teardown warning
after all gate content had already printed PASS — confirmed as flaky test-exit
hygiene debt, not a real gate failure, via a clean rerun with exit code 0.

## Change status: COMPLETE (both PRs)

All 16 tasks done, all acceptance criteria from spec.md satisfied, full
verification suite (including coverage gate and release gate) passes on a
clean run. Nothing has been committed or pushed — working tree only, per
"never commit unless the user explicitly asks."

## PR boundary / workload

- PR 1 (this PR): Tasks 1–8, watcher abstraction + lifecycle service
  (`folder_watcher.py`, `library_watch_service.py`) + their unit tests.
  Inert/unreferenced by the rest of the app — safe to land alone. Rollback:
  delete both new modules and their tests.
- PR 2 (next): Tasks 9–16, `scan_service.py` integration hooks, `AppState`
  field, Library-screen UI affordance, lifecycle edge-case tests, final full
  verification suite (including coverage gate and
  `scripts/release_gate_check.py`).
- Chain strategy: stacked-to-main — PR 1 merges to main first upon approval;
  PR 2 builds on top of main once PR 1 has landed.

## Structured status consumed / produced

- Consumed: `delivery_strategy=ask-on-risk` (already resolved to chained
  PRs), `chain_strategy=stacked-to-main`, PR 1 of 2 boundary — all supplied
  in the apply launch prompt, consistent with tasks.md's own Review Workload
  Forecast (`Decision needed before apply: Resolved`).
  `actionContext`/native SDD status was not separately queried by this
  sub-agent; the launch prompt explicitly scoped this batch to Tasks 1–6
  (interpreted per tasks.md's actual numbering as Tasks 1–8, since tasks.md's
  own PR 1 boundary is Task 8's VERIFY gate, not Task 6) and named the exact
  in-scope/out-of-scope files, which this apply followed.
- Produced: this `apply-progress.md`, updated `tasks.md` checkboxes (Tasks
  1–8, all `- [x]`), no `state.yaml` update performed (not requested in the
  launch scope; recommend the orchestrator update `state.yaml`'s
  `phases.apply` to `in-progress` with a note that PR 1 of 2 is complete and
  PR 2 remains).
