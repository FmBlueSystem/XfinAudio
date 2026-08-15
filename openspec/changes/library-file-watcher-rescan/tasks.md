# Tasks: Library File Watcher — Detect Changes, Prompt Rescan

Strict TDD. Test runner: `uv run pytest -q`. Every behavior-changing task
follows RED → GREEN → REFACTOR → VERIFY. Build order follows design.md's
stated dependency chain: dependency pin → library-layer abstraction (fake
seam) → desktop-layer lifecycle service (fake seams) → `scan_service.py`
integration hooks → `AppState` field → Library screen UI wiring →
lifecycle edge-case tests → full verification suite.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380–480 (see breakdown below) |
| 400-line budget risk | Medium-High |
| Chained PRs recommended | Yes (recommended; final call is ask-on-risk) |
| Suggested split | Revised after PR 1 actuals came in at 525 lines (original 200–240 estimate for Tasks 1–8 was too low — debounce/threading test coverage was heavier than forecast): PR 1a: `folder_watcher.py` + `test_folder_watcher.py` (166 lines) → PR 1b: `library_watch_service.py` + `test_library_watch_service.py` + `pyproject.toml`/`uv.lock` watchdog pin (358 lines) → PR 2: `scan_service.py` integration + `AppState` field + UI affordance + lifecycle edge-case tests + full verification (Tasks 9–16) |
| Delivery strategy | ask-on-risk — chained PRs confirmed by user |
| Chain strategy | stacked-to-main — each PR merges to main in order upon approval |

```text
Decision needed before apply: Resolved
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium-High
```

Line estimate breakdown:

- `pyproject.toml` / `uv.lock`: ~2 + lockfile regeneration (lockfile diff not
  counted against the 400-line human-review budget per project convention,
  but noted here for completeness).
- `src/xfinaudio/library/folder_watcher.py` (new): ~55–70 lines (`Protocol`,
  `WatchdogEventSource`, `FolderWatcher`).
- `tests/test_folder_watcher.py` (new): ~60–80 lines (`FakeEventSource` +
  start/stop/is_watching/replace-watch tests).
- `src/xfinaudio/desktop/library_watch_service.py` (new): ~90–110 lines
  (`LibraryWatchService`, `DebounceTimer` protocol, `_qtimer_factory`).
- `tests/test_library_watch_service.py` (new): ~90–120 lines (debounce
  coalescing, pause/resume, single-watch invariant, cross-thread marshal).
- `src/xfinaudio/desktop/scan_service.py`: ~15–20 lines (pause/resume/start
  call-outs + `set_watch_service` setter).
- `tests/test_scan_service.py`: ~25–35 lines (spy `LibraryWatchService`
  fixture + pause/resume/start/clear assertions).
- `src/xfinaudio/desktop/app_state.py`: ~1 line (new field).
- `src/xfinaudio/desktop/library_screen_builder.py`,
  `screens/library_screen.py`, `library_view_model.py`,
  `library_screen_rendering.py`: ~20–30 lines combined.
- `tests/test_library_screen.py` / `tests/test_library_view_model.py`:
  ~20–30 lines combined.

Given the Medium-High risk and the natural two-module seam already implied
by design.md (library-layer abstraction is independently testable and
mergeable before the desktop-layer consumer touches it), **chained PRs are
recommended**. The orchestrator must apply the cached `delivery_strategy`
(`ask-on-risk`) and collect `chain_strategy` from the user before `sdd-apply`
begins, per the Review Workload Guard.

---

## Task 1 — Dependency: pin `watchdog`

Satisfies: proposal Dependencies; spec "Watcher observes the currently
scanned folder" (OS-level watch mechanism).

- [x] Add `"watchdog>=4.0,<7.0"` to `pyproject.toml` `[project].dependencies`,
      alphabetically placed alongside the existing pinned entries.
- [x] Run `uv lock` to regenerate `uv.lock`.
- [x] Run `uv run pyright` project-wide to confirm `watchdog`'s bundled types
      (or absence thereof) do not break the current zero-error baseline. If
      stubs are insufficient, note it — Task 2's `FileSystemEventSource`
      Protocol seam isolates the rest of the app from `watchdog`'s types
      regardless.
- [x] Verify: `uv run pytest -q` still fully green (no behavior touched yet).

Parallelizable: No — this is the first step; nothing else can `import
watchdog` before it lands.

---

## Task 2 — RED: `library/folder_watcher.py` abstraction tests (fake event source)

Satisfies: spec "Watcher observes the currently scanned folder" (both
scenarios).

- [x] Create `tests/test_folder_watcher.py` with a `FakeEventSource` class
      implementing the `FileSystemEventSource` Protocol from design.md §2.1:
      records `start(folder, on_raw_event)` / `stop()` calls, exposes a
      `fire(path)` helper to synchronously invoke the captured
      `on_raw_event` callback.
- [x] Write tests against `FolderWatcher(event_source=FakeEventSource())`:
  - `test_start_arms_watch_on_folder` — `start()` calls
    `event_source.start(folder, callback)` and `is_watching` becomes `True`.
  - `test_stop_stops_watch` — `stop()` calls `event_source.stop()`,
    `is_watching` becomes `False`.
  - `test_stop_is_noop_when_not_watching` — `stop()` with no active watch
    does not call `event_source.stop()`.
  - `test_start_replaces_previous_watch` — calling `start()` twice stops the
    first watch (`event_source.stop()` called) before arming the second.
  - `test_event_before_start_never_fires` — `fire()` before any `start()`
    call is a no-op (no callback registered yet on the fake).
- [x] Run focused: `uv run pytest -q tests/test_folder_watcher.py`. Expected
      **FAIL** (RED) — `xfinaudio.library.folder_watcher` does not exist yet.

Parallelizable: Yes — independent of Task 1 landing in `uv.lock` as long as
`watchdog` is declared (no runtime import needed for these fake-seam tests).

---

## Task 3 — GREEN: implement `library/folder_watcher.py`

Satisfies: same as Task 2.

- [x] Create `src/xfinaudio/library/folder_watcher.py` per design.md §2.1:
      `FileSystemEventSource` Protocol, `WatchdogEventSource` (wraps
      `watchdog.observers.Observer` + `watchdog.events.FileSystemEventHandler`
      — the only module importing `watchdog` directly), and `FolderWatcher`
      (`start`, `stop`, `is_watching` property). `FolderWatcher` does not
      debounce; it forwards every raw event unfiltered.
- [x] Run focused: `uv run pytest -q tests/test_folder_watcher.py`. Expected
      **PASS** (GREEN).
- [x] Run `uv run pyright src/xfinaudio/library/folder_watcher.py
      tests/test_folder_watcher.py`. Expected 0 errors.

Parallelizable: No — depends on Task 2 (RED confirmed first) and Task 1
(`watchdog` declared as a dependency).

---

## Task 4 — REFACTOR: `folder_watcher.py`

- [x] Review `FolderWatcher`/`WatchdogEventSource` for naming/formatting
      consistency with neighboring `library/` modules (e.g.
      `library/scan_service.py`). No behavior change expected.
- [x] Run `uv run pytest -q tests/test_folder_watcher.py` to confirm still
      green after any refactor.

---

## Task 5 — RED: `desktop/library_watch_service.py` lifecycle & debounce tests (fake seams)

Satisfies: spec "Filesystem changes are debounced before surfacing" (both
scenarios), "Watcher lifecycle is tied to scan state and folder selection"
(pause/resume, folder-switch, shutdown scenarios), "State updates follow
immutable AppState conventions".

- [x] Create `tests/test_library_watch_service.py` with a
      `FakeDebounceTimer` implementing the `DebounceTimer` Protocol from
      design.md §2.2 (`start(msec)`, `stop()`, `is_active()`, plus a test-only
      `fire()` to synchronously invoke the timeout callback) and a fake
      `FolderWatcher` (or reuse `FakeEventSource` through a real
      `FolderWatcher` instance — prefer the real `FolderWatcher` + fake event
      source per design.md's layering, since `FolderWatcher` itself is now
      GREEN and trustworthy).
- [x] Write tests against `LibraryWatchService` constructed with injected
      `folder_watcher` and `debounce_timer_factory`:
  - `test_start_arms_watcher_on_folder` — `start(folder)` calls through to
    the injected `FolderWatcher.start`.
  - `test_raw_event_restarts_debounce_timer` — firing a raw event (re)starts
    the debounce timer with `settle_window_ms`.
  - `test_burst_of_events_coalesces_to_single_emission` — firing multiple raw
    events before the fake timer's `fire()` results in exactly one
    `changes_detected` signal emission when `fire()` is finally called.
  - `test_timeout_sets_state_via_model_copy` — a fake/stub state object with
    a `model_copy` spy confirms `changes_detected_since_scan=True` is applied
    via `model_copy(update=...)`, never via direct attribute mutation.
  - `test_pause_stops_watch_and_remembers_folder` — `pause()` stops the
    underlying watch and debounce timer; `is_watching`-equivalent state
    reflects paused.
  - `test_resume_rearms_previously_paused_folder` — `resume()` after
    `pause()` re-arms the same folder via `start()`.
  - `test_pause_without_active_watch_is_noop` / `test_resume_without_pause_is_noop`
    — symmetric no-op guards matching `ScanService.cancel()`'s idempotent
    style.
  - `test_stop_stops_watch_and_clears_pause_state` — `stop()` clears both
    active-watch and paused-folder bookkeeping (app shutdown path).
  - `test_start_after_previous_watch_switches_folder` — calling `start()`
    with a new folder while already watching folder A stops A first (asserts
    on the underlying `FolderWatcher`/event-source stop call).
- [x] Run focused: `uv run pytest -q tests/test_library_watch_service.py`.
      Expected **FAIL** (RED) — `xfinaudio.desktop.library_watch_service`
      does not exist yet.

Parallelizable: No — depends on Task 3 (`FolderWatcher` GREEN) if reusing the
real `FolderWatcher` class; independent of Tasks 6–14 otherwise.

---

## Task 6 — GREEN: implement `desktop/library_watch_service.py`

Satisfies: same as Task 5.

- [x] Create `src/xfinaudio/desktop/library_watch_service.py` per design.md
      §3.1: `LibraryWatchService(QObject)` with `changes_detected` Signal,
      `start`/`stop`/`pause`/`resume`, internal `_raw_event_received =
      Signal(str)` cross-thread marshal, `@Slot(str)` handler that (re)starts
      the debounce timer, `_on_settle_timeout` that applies
      `state.model_copy(update={"changes_detected_since_scan": True})` and
      emits `changes_detected`, and `set_state_accessors(state, sync_state)`
      matching `ScanService`'s setter-injection pattern.
- [x] Run focused: `uv run pytest -q tests/test_library_watch_service.py`.
      Expected **PASS** (GREEN).
- [x] Add one Qt-harness test (`qtbot`/`QSignalSpy`, consistent with existing
      Qt-slot tests in this codebase) confirming the cross-thread marshal:
      calling `_on_raw_event_background_thread` from a plain Python thread
      results in `_on_raw_event_main_thread` executing on the Qt main thread
      and the debounce timer starting. Expected **PASS**.
- [x] Run `uv run pyright src/xfinaudio/desktop/library_watch_service.py
      tests/test_library_watch_service.py`. Expected 0 errors.

Parallelizable: No — depends on Task 5.

---

## Task 7 — REFACTOR: `library_watch_service.py`

- [x] Review for naming/formatting consistency with `scan_service.py`
      (structural mirror per design.md §3.1). No behavior change expected.
- [x] Run `uv run pytest -q tests/test_library_watch_service.py
      tests/test_folder_watcher.py` to confirm still green.

---

## Task 8 — VERIFY: watcher-abstraction + lifecycle-service slice (PR 1 boundary)

- [x] `uv run pytest -q tests/test_folder_watcher.py
      tests/test_library_watch_service.py`
- [x] `uv run pyright src/xfinaudio/library/folder_watcher.py
      src/xfinaudio/desktop/library_watch_service.py
      tests/test_folder_watcher.py tests/test_library_watch_service.py`
- [x] `uv run ruff check src/xfinaudio/library/folder_watcher.py
      src/xfinaudio/desktop/library_watch_service.py`
- [x] `uv run ruff format --check src/xfinaudio/library/folder_watcher.py
      src/xfinaudio/desktop/library_watch_service.py`

**PR 1 boundary** (if chaining): watcher abstraction + lifecycle service are
independently mergeable here — no other production module references either
new module yet, so this slice is inert (dead code, not yet wired) and safe
to land alone. Rollback: delete both new modules and their tests; nothing
else references them.

---

## Task 9 — RED: `AppState` new field + `scan_service.py` integration tests

Satisfies: spec "State updates follow immutable AppState conventions";
"Watcher lifecycle is tied to scan state and folder selection" (pause during
scan, resume/re-arm after, folder-switch scenarios); "The affordance invokes
the existing scan pipeline unchanged" (state clears on completion).

- [x] In `tests/test_scan_service.py`, add a spy `FakeLibraryWatchService`
      (records `pause()`/`resume()`/`start(folder)` calls) injected via a new
      `ScanService.set_watch_service(watch_service)` setter (or constructor
      param, matching the existing setter-injection style of
      `set_state_accessors`/`set_ui`/`set_actions`).
- [x] Write tests:
  - `test_begin_scan_state_pauses_watch_service` — `begin_scan_state()` calls
    `watch_service.pause()` when a watch service is wired.
  - `test_end_scan_state_resumes_watch_service` — `_end_scan_state()` (via
    `on_completed`/`on_failed`/cancel path) calls `watch_service.resume()`.
  - `test_successful_scan_arms_watch_on_scanned_folder` — `on_completed()`
    non-cancelled branch calls `watch_service.start(folder)` with the
    scanned folder.
  - `test_successful_scan_clears_changes_detected_state` — `on_completed()`
    non-cancelled branch applies
    `state.model_copy(update={"changes_detected_since_scan": False})`.
  - `test_scan_service_works_without_watch_service_wired` — none of the above
    calls raise when no `watch_service` was set (defaults to `None`,
    `ScanService` remains independently testable per design.md §4).
- [x] Run focused: `uv run pytest -q tests/test_scan_service.py -k watch_service`.
      Expected **FAIL** (RED).

Parallelizable: No — depends on Task 6 (`LibraryWatchService` GREEN, so the
fake/spy shape matches the real class's public methods) but is otherwise
independent of Tasks 10–14 until Task 10 lands.

---

## Task 10 — GREEN: wire `scan_service.py` pause/resume/start/clear hooks

Satisfies: same as Task 9.

- [x] In `src/xfinaudio/desktop/scan_service.py`: add `_watch_service:
      LibraryWatchService | None = None` and a `set_watch_service()` setter.
  - `begin_scan_state()`: after
    `self.current_scan_cancellation_token = ScanCancellationToken()`, call
    `self._watch_service.pause()` if wired.
  - `_end_scan_state()`: call `self._watch_service.resume()` if wired (before
    `_refresh_idle_action_state()`/`_sync_state()`).
  - `on_completed()` non-cancelled branch, after
    `self._set_scanned_records(result.records)`: call
    `self._watch_service.start(folder)` (via `self._selected_folder()`) if
    wired and folder is not `None`; apply
    `self._state = self._state.model_copy(update={"changes_detected_since_scan": False})`
    unconditionally (independent of whether a watch service is wired, per
    design.md §4).
- [x] Run focused: `uv run pytest -q tests/test_scan_service.py`. Expected
      **PASS** (GREEN), full file still green (no regression in existing
      scan-service tests).
- [x] Run `uv run pyright src/xfinaudio/desktop/scan_service.py
      tests/test_scan_service.py`. Expected 0 errors.

Parallelizable: No — depends on Task 9.

---

## Task 11 — RED+GREEN: `AppState.changes_detected_since_scan` field

Satisfies: spec "State updates follow immutable AppState conventions".

- [x] RED: in an `AppState`-focused test file (e.g.
      `tests/test_app_state.py` if it exists, else add to
      `tests/test_scan_service.py` or the most relevant existing state test
      module), add `test_app_state_has_changes_detected_since_scan_default_false`
      asserting `AppState().changes_detected_since_scan is False`. Run
      focused; expected **FAIL** (attribute does not exist).
- [x] GREEN: in `src/xfinaudio/desktop/app_state.py`, add
      `changes_detected_since_scan: bool = False` to the "Library / Scan"
      field group (near `records_by_path`). Run focused; expected **PASS**.
- [x] Run `uv run pyright src/xfinaudio/desktop/app_state.py`. Expected 0
      errors.

Parallelizable: Can run alongside Task 9/10 (different file), but Task 10's
`on_completed` edit references this field, so land Task 11 no later than
immediately before Task 10's GREEN step.

---

## Task 12 — RED: Library screen `rescan_button` affordance tests

Satisfies: spec "Changes are surfaced as a user-actionable affordance, never
an automatic rescan" (both scenarios); "The affordance invokes the existing
scan pipeline unchanged".

- [x] In the relevant existing view-model test module (e.g.
      `tests/test_library_view_model.py`), add
      `test_rescan_button_visible_when_changes_detected_and_not_scanning`
      and `test_rescan_button_hidden_when_scanning_or_no_changes` for
      `LibraryViewModel.rescan_button_visible(state)`.
- [x] In the relevant existing screen test module (e.g.
      `tests/test_library_screen.py`), add
      `test_rescan_button_click_calls_scan_selected_folder` asserting
      `rescan_requested` → `window.scan_selected_folder` wiring (same pattern
      as the existing `scan_button` click test).
- [x] Run focused: `uv run pytest -q tests/test_library_view_model.py
      tests/test_library_screen.py -k rescan`. Expected **FAIL** (RED).

Parallelizable: Yes — independent of Tasks 9–11 (different files), can run
in parallel with that track.

---

## Task 13 — GREEN: wire `rescan_button` UI affordance

Satisfies: same as Task 12.

- [x] `library_screen_builder.py`: add `screen.rescan_button = QPushButton(...)`
      next to `scan_button`/`cancel_button` per design.md §6.1
      (`setObjectName("secondaryAction")`, `setVisible(False)` initial).
- [x] `screens/library_screen.py`: add `rescan_requested = Signal()`, connect
      `rescan_button.clicked` to it, and in `connect_signals()` connect
      `rescan_requested` to `window.scan_selected_folder` (identical target
      slot as `scan_button`).
- [x] `library_view_model.py`: add
      `rescan_button_visible(self, state: AppState) -> bool` returning
      `state.changes_detected_since_scan and not state.is_scanning`.
- [x] `library_screen_rendering.py`: in `render()`, add
      `self.rescan_button.setVisible(vm.rescan_button_visible(state))`
      alongside the existing `cancel_button.setVisible(...)` line.
- [x] Add tooltip/accessible-name entries to `_setup_button_tooltips()` and
      `_setup_accessibility()`, and tab-order entry immediately after
      `cancel_button` in `_setup_tab_order()`, per design.md §6.5.
- [x] Run focused: `uv run pytest -q tests/test_library_view_model.py
      tests/test_library_screen.py`. Expected **PASS** (GREEN).
- [x] Run `uv run pyright` on all four touched UI files. Expected 0 errors.

Parallelizable: No — depends on Task 12 and on Task 11 (`AppState` field
must exist for `rescan_button_visible` to compile/typecheck).

---

## Task 14 — REFACTOR: integration + UI slice

- [x] Review `scan_service.py` hooks and UI wiring for naming/formatting
      consistency with existing neighbors (`scan_button`/`cancel_button`
      pattern, `_end_scan_state` structure). No behavior change expected.
- [x] Run `uv run pytest -q tests/test_scan_service.py
      tests/test_library_view_model.py tests/test_library_screen.py` to
      confirm still green.

---

## Task 15 — Lifecycle edge-case tests (design.md §9 integration matrix)

Satisfies: spec "Watcher lifecycle is tied to scan state and folder
selection" (all three scenarios, integration-level), "Filesystem changes are
debounced before surfacing" (integration-level burst coalescing through the
real `LibraryWatchService` + real `FolderWatcher` pairing, still with a fake
`FileSystemEventSource`/`DebounceTimer` — no real filesystem or wall-clock
timing per design.md §9).

- [x] `test_folder_switch_stops_old_watch_and_arms_new` — end-to-end through
      `LibraryWatchService.start()` called twice with different folders,
      asserting the old folder's watch stopped before the new one armed
      (spec: "Switching folders re-arms the watch").
- [x] `test_shutdown_stops_watcher_with_no_leaked_threads` — `stop()` clears
      all internal state and the underlying fake event source records
      exactly one `stop()` call; assert no dangling timer remains active
      (`debounce_timer.is_active() is False` after `stop()`).
  - [x] If the real `WatchdogEventSource` needs a smoke check against an
      actual temp directory, add ONE explicitly marked slow/integration test
      (`@pytest.mark.slow` or existing project convention for such markers)
      isolated from the rest of the suite, per design.md §9's "kept minimal
      and separate from the RED-phase unit suite." Do not gate the default
      `pytest -q` run on it if the project's default marker selection
      excludes slow tests.
- [x] `test_pause_during_scan_does_not_self_trigger_from_scan_reads` —
      integration test through `ScanService` + injected
      `FakeLibraryWatchService`/real `LibraryWatchService` with fake
      `FileSystemEventSource`: begin a scan, fire raw events on the paused
      watcher's underlying fake source (simulating a stray callback), assert
      no `changes_detected` emission occurs while paused.
- [x] `test_burst_across_scan_service_and_watch_service_coalesces_once` —
      confirms a burst of events firing after `resume()` still coalesces to
      one `changes_detected_since_scan=True` transition, not one per event,
      exercising the full pause→resume→debounce chain together.
- [x] Run focused: `uv run pytest -q tests/test_library_watch_service.py
      tests/test_scan_service.py -k "shutdown or folder_switch or pause_during_scan or burst"`.
      Expected **PASS** (GREEN, since Tasks 6/10 already implement the
      underlying behavior — these are triangulation/integration tests, not
      new production code).

Parallelizable: No — depends on Tasks 10 and 6 both being GREEN (exercises
both `ScanService` and `LibraryWatchService` together).

---

## Task 16 — VERIFY: full suite (final gate)

Satisfies: proposal Success Criteria — "Full verification suite... passes".

- [x] `uv run pytest -q` (full suite, no `-k` filter) — expect 100% pass,
      zero regressions in pre-existing tests.
- [x] `uv run pytest --cov` (or the project's existing coverage-gate
      invocation) — confirm the coverage gate threshold is still met.
- [x] `uv run pyright` (project-wide) — expect 0 errors.
- [x] `uv run ruff check .` — expect 0 findings.
- [x] `uv run ruff format --check .` — expect no reformat needed.
- [x] Run the project's release gate script (per `AGENTS.md`) — expect exit
      0.
- [x] Confirm `uv.lock` is committed and resolves cleanly
      (`uv lock --check` or equivalent, if the project uses that check in
      CI).
- [x] Cross-check every proposal Success Criteria checkbox and every spec
      Acceptance Criteria checkbox against the implemented behavior and its
      asserting test(s); do not check a box on prose alone.

**PR 2 boundary** (if chaining): this task, plus Tasks 9–15, form the second
slice — `scan_service.py` integration, `AppState` field, UI affordance, and
lifecycle edge-case tests, landing on top of PR 1's inert watcher modules and
activating them for the first time. Rollback: revert the `scan_service.py`
hooks, the `AppState` field, and the UI wiring; PR 1's modules remain valid,
unreferenced code (or revert PR 1 too, if a full rollback is desired).

---

## Parallelization Summary

- Track A (sequential, required first): Task 1 (dependency pin).
- Track B (depends on Track A): Task 2 → 3 → 4 (folder_watcher.py).
- Track C (depends on Track B): Task 5 → 6 → 7 (library_watch_service.py).
- Task 8 is the PR 1 verification/boundary gate — cannot run until Track C
  is green.
- Track D (depends on Track C for the spy shape, and on Task 11 landing
  before Task 10's GREEN step): Task 9 → 10 (scan_service.py wiring).
- Task 11 (AppState field) can run in parallel with Track D's RED step
  (Task 9) but must land before Task 10's GREEN step.
- Track E (independent of Track D, different files): Task 12 → 13 (UI
  affordance) — depends on Task 11 for typechecking, not on Task 9/10.
- Task 14 is refactor over Tracks D+E combined.
- Task 15 (lifecycle edge cases) depends on both Track D (Task 10) and Track
  C (Task 6) being green — it exercises both services together.
- Task 16 is the final sequential full-suite gate; cannot run until Task 15
  is green.
- Given the Medium-High size risk, true chaining (PR 1 = Tracks B+C+Task 8,
  PR 2 = Tracks D+E+Tasks 14–16) is recommended over a single-PR slice. The
  orchestrator must confirm `chain_strategy` with the user before `sdd-apply`
  begins, per the Review Workload Guard.
