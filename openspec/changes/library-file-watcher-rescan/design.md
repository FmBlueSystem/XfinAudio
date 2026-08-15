# Design: Library File Watcher — Detect Changes, Prompt Rescan

Change: `library-file-watcher-rescan`
Capability: `library-file-watcher` (see `openspec/specs/library-file-watcher/spec.md`)

## 1. Overview

Two new modules mirror the existing scan-service split between a plain-Python
library-layer worker and a Qt-owning desktop-layer service:

- `src/xfinaudio/library/folder_watcher.py` — plain-Python abstraction over
  `watchdog`'s `Observer`/event handler. No Qt dependency, no debounce timing
  of its own beyond exposing raw settled/unsettled event notifications through
  an injectable clock-free seam so RED tests never depend on real filesystem
  or wall-clock timing.
- `src/xfinaudio/desktop/library_watch_service.py` — `QObject` lifecycle
  owner, structurally mirroring `ScanService`: owns the `FolderWatcher`
  instance, runs the actual OS watch/`Observer` thread management, owns a
  `QTimer`-based debounce on the Qt main thread, and updates `AppState` via
  `model_copy(update=...)` when a settled change is detected.

`scan_service.py` gains two new call-outs (pause before scan, resume after)
at its two existing lifecycle seams (`begin_scan_state()` /
`_end_scan_state()`), and Library-screen wiring gains one new button plus one
new view-model predicate, following the exact `scan_button` /
`scan_button_enabled` pattern already in place.

```
watchdog.Observer (OS-level, background thread)
        │ raw filesystem events
        ▼
FolderWatcher (library/folder_watcher.py)
  - wraps Observer + event handler
  - start(folder) / stop()
  - forwards each raw event via on_event callback (no debounce here)
        │ on_event(path) — called from watchdog's own thread
        ▼
LibraryWatchService (desktop/library_watch_service.py)
  - QObject, owns FolderWatcher instance
  - marshals on_event to Qt main thread via Signal (thread-safe)
  - QTimer(singleShot) debounce: (re)start timer on each event; on
    timeout, emit changes_detected signal
  - pause()/resume() to stop/restart underlying watch during scans
        │ changes_detected signal (Qt main thread)
        ▼
MainWindow / scan_service wiring
  - state = state.model_copy(update={"changes_detected_since_scan": True})
  - Library screen renders "Changes detected — Rescan" affordance
        │ user clicks affordance
        ▼
ScanService.scan_selected_folder()  (unchanged)
```

## 2. `library/folder_watcher.py`

### 2.1 Interface

```python
"""App-owned abstraction over watchdog's Observer, decoupled from its types."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class FileSystemEventSource(Protocol):
    """Seam: anything that can start/stop watching a folder and report raw
    create/modify/delete events for paths under it. watchdog's Observer
    satisfies this at runtime; tests substitute a fake."""

    def start(self, folder: Path, on_raw_event: Callable[[str], None]) -> None: ...
    def stop(self) -> None: ...


class WatchdogEventSource:
    """Real implementation: wraps watchdog.observers.Observer +
    watchdog.events.FileSystemEventHandler. The only module that imports
    `watchdog` directly."""

    def __init__(self) -> None:
        self._observer: Any | None = None  # watchdog.observers.Observer

    def start(self, folder: Path, on_raw_event: Callable[[str], None]) -> None: ...
    def stop(self) -> None: ...


class FolderWatcher:
    """Public abstraction. Debounce/coalesce is NOT implemented here — this
    class only starts/stops the OS watch and forwards each raw event
    unfiltered. Debounce is the desktop-layer's job (QTimer, Qt main thread),
    matching the existing ScanService._request_sync coalescing pattern."""

    def __init__(self, event_source: FileSystemEventSource | None = None) -> None:
        self._event_source = event_source or WatchdogEventSource()
        self._watching_folder: Path | None = None

    def start(self, folder: Path, on_event: Callable[[str], None]) -> None:
        """Start watching *folder* recursively. Replaces any active watch."""
        self.stop()
        self._watching_folder = folder
        self._event_source.start(folder, on_event)

    def stop(self) -> None:
        """Stop the active watch, if any. No-op if not watching."""
        if self._watching_folder is not None:
            self._event_source.stop()
            self._watching_folder = None

    @property
    def is_watching(self) -> bool:
        return self._watching_folder is not None
```

Design decisions:

- `FolderWatcher` itself does **not** debounce. The proposal frames debounce
  as a `QTimer`-based concern "consistent with the existing coalesced
  `_request_sync` pattern in `ScanService`" — that pattern lives entirely in
  the Qt/desktop layer today (`ScanService._request_sync`, wired via
  `set_actions(request_sync=...)`). Keeping `FolderWatcher` Qt-free and
  debounce-free means the library layer stays a thin, swappable seam and all
  Qt-thread-timing complexity lives in one place (`LibraryWatchService`),
  exactly where `ScanService` already puts its own coalescing.
- `on_event` fires on **watchdog's own background thread**, not the Qt main
  thread — this mirrors how `ScanWorker` runs on a `QThread` and only
  crosses back via `Signal`/`Slot`. `LibraryWatchService` is responsible for
  the thread-safe marshal (Section 3.2).
- The `FileSystemEventSource` Protocol is the RED-test seam: tests inject a
  `FakeEventSource` that records `start()`/`stop()` calls and lets the test
  call `on_raw_event(path)` synchronously and directly, with zero real
  filesystem I/O and zero real timing. `FolderWatcher`'s own behavior (does
  it call `stop()` before re-`start()`? does `is_watching` reflect state
  correctly? does an event before `start()` never fire?) is fully testable
  against the fake with deterministic, instant test execution.

### 2.2 Debounce/coalesce testability without real filesystem timing

The settle-window debounce itself (Section 3.3) lives in
`LibraryWatchService` and uses `QTimer`. That is tested the same way the
codebase already tests Qt-timer-driven code: inject a fake/controllable timer
seam rather than sleeping in tests. Concretely:

```python
class DebounceTimer(Protocol):
    """Seam over QTimer so tests can trigger a timeout deterministically."""
    def start(self, msec: int) -> None: ...
    def stop(self) -> None: ...
    def is_active(self) -> bool: ...
    # timeout callback is passed once at construction, not per-start
```

`LibraryWatchService` accepts an optional `debounce_timer_factory` (defaults
to a small `QTimer` adapter). RED tests construct `LibraryWatchService` with
a `FakeDebounceTimer` that exposes `fire()` to synchronously invoke the
timeout callback — no `QTest.qWait`, no real 2-second sleep, no flakiness.
This is the same "inject the seam, keep production code Qt-real" shape as
`FileSystemEventSource` above, applied one layer up.

## 3. `desktop/library_watch_service.py`

### 3.1 Structural mirror of `ScanService`

Same shape as `scan_service.py`:

```python
class LibraryWatchService(QObject):
    """Qt-thread-safe lifecycle owner for filesystem-change detection."""

    changes_detected = Signal()

    def __init__(
        self,
        folder_watcher: FolderWatcher | None = None,
        *,
        debounce_timer_factory: Callable[[Callable[[], None]], DebounceTimer] | None = None,
        settle_window_ms: int = 2000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._folder_watcher = folder_watcher or FolderWatcher()
        self._settle_window_ms = settle_window_ms
        self._debounce_timer_factory = debounce_timer_factory or _qtimer_factory
        self._debounce_timer = self._debounce_timer_factory(self._on_settle_timeout)
        self._watched_folder: Path | None = None
        self._paused_folder: Path | None = None  # folder to resume onto, while paused
        self._state: Any = None
        self._sync_state: Callable[[], None] = _unwired

        # Internal signal used purely to marshal watchdog's background-thread
        # callback onto the Qt main thread — the same pattern QThread workers
        # use via Signal/Slot instead of touching Qt objects cross-thread.
        self._raw_event_received.connect(self._on_raw_event_main_thread)

    _raw_event_received = Signal(str)  # internal cross-thread marshal

    def set_state_accessors(self, *, state: Any, sync_state: Callable[[], None]) -> None:
        self._state = state
        self._sync_state = sync_state

    # -- lifecycle --------------------------------------------------------

    def start(self, folder: Path) -> None:
        """Arm the watch on *folder*, stopping any previous watch."""
        self._debounce_timer.stop()
        self._watched_folder = folder
        self._paused_folder = None
        self._folder_watcher.start(folder, self._on_raw_event_background_thread)

    def stop(self) -> None:
        """Stop the watch entirely (app shutdown, explicit teardown)."""
        self._debounce_timer.stop()
        self._folder_watcher.stop()
        self._watched_folder = None
        self._paused_folder = None

    def pause(self) -> None:
        """Stop the OS watch for the duration of an in-flight scan, but
        remember the folder so resume() can re-arm it."""
        if self._watched_folder is None:
            return
        self._debounce_timer.stop()
        self._paused_folder = self._watched_folder
        self._folder_watcher.stop()
        self._watched_folder = None

    def resume(self) -> None:
        """Re-arm the watch on the folder that was active before pause()."""
        if self._paused_folder is None:
            return
        folder = self._paused_folder
        self._paused_folder = None
        self.start(folder)

    # -- event handling -----------------------------------------------------

    def _on_raw_event_background_thread(self, path: str) -> None:
        # Called on watchdog's own thread. Never touch Qt objects here beyond
        # emitting a Signal, which Qt marshals safely across threads.
        self._raw_event_received.emit(path)

    @Slot(str)
    def _on_raw_event_main_thread(self, path: str) -> None:
        # Now safely on the Qt main thread: (re)start the debounce timer.
        self._debounce_timer.start(self._settle_window_ms)

    def _on_settle_timeout(self) -> None:
        if self._state is not None:
            self._state = self._state.model_copy(update={"changes_detected_since_scan": True})
        self.changes_detected.emit()
        self._sync_state()
```

Notes:

- The cross-thread marshal (`Signal(str)` → `@Slot(str)`) is the Qt-idiomatic
  way to move a callback fired on watchdog's background observer thread onto
  the Qt main thread, mirroring how `ScanWorker.progress`/`finished`/`failed`
  signals cross from the `QThread` worker back to `ScanService`'s slots. It
  is the smallest correct primitive for this — no manual locking, no
  `QMetaObject.invokeMethod` needed, and it composes cleanly with the
  `DebounceTimer` seam.
- `pause()`/`resume()` are symmetric and idempotent: `pause()` on an already-
  paused/stopped service is a no-op; `resume()` with nothing paused is a
  no-op. This matches `ScanService.cancel()`'s style of guarding against
  double-invocation rather than asserting preconditions.
- `_debounce_timer` is (re)started on every raw event and only fires once no
  further events arrive within `settle_window_ms` — a `QTimer.start()` call
  on an already-running `QTimer` restarts its countdown, which is exactly
  the coalesce semantics required (burst of events → timer keeps getting
  pushed back → single `changes_detected` emission once the burst stops).

### 3.2 Ownership and wiring (mirrors `ScanService.set_state_accessors` / `set_actions`)

`LibraryWatchService` is constructed and wired the same way `ScanService`
is — in the window/service wiring module (`window_service_wiring.py` or
equivalent composition root), given `state` and `sync_state` accessors via a
`set_state_accessors` call, not by importing `AppState`/`MainWindow`
directly. This keeps it testable in isolation exactly like `ScanService`.

## 4. Integration with `scan_service.py`

Two call-outs at `ScanService`'s two existing lifecycle transition points.
`ScanService` is given an optional `watch_service: LibraryWatchService |
None` collaborator (constructor or a `set_watch_service()` setter, matching
the existing setter-injection style of `set_state_accessors`/`set_ui`/
`set_actions`), defaulting to `None` so `ScanService` remains independently
testable without a live watch service.

- **Pause, before scan starts** — in `begin_scan_state()`, immediately after
  `self.current_scan_cancellation_token = ScanCancellationToken()`:

  ```python
  def begin_scan_state(self) -> None:
      self._require_wired()
      self.current_scan_cancellation_token = ScanCancellationToken()
      if self._watch_service is not None:
          self._watch_service.pause()
      ...
  ```

- **Resume, after scan ends (success, failure, or cancel)** — in
  `_end_scan_state()`, which is the single method already called from both
  `on_completed()` (including the early-return cancel branch) and
  `on_failed()`:

  ```python
  def _end_scan_state(self) -> None:
      self.current_scan_cancellation_token = None
      self._state.scan_progress_count = 0
      if self._watch_service is not None:
          self._watch_service.resume()
      self._refresh_idle_action_state()
      self._sync_state()
  ```

  `_end_scan_state()` is the correct single hook: it already unifies the
  cancel path (`on_completed` with `result.cancelled`), the success path
  (`on_completed` normal flow), and the failure path (`on_failed`) — so pause
  and resume are guaranteed symmetric without duplicating the resume call at
  three call sites.

- **(Re-)arm after a successful scan of a (possibly new) folder** — also in
  `on_completed()`, in the non-cancelled branch, after
  `self._set_scanned_records(result.records)`:

  ```python
  self._set_scanned_records(result.records)
  if self._watch_service is not None:
      folder = self._selected_folder()
      if folder is not None:
          self._watch_service.start(folder)
  ```

  Calling `start()` unconditionally here — rather than a separate "is this a
  new folder?" branch — is deliberate: `LibraryWatchService.start()` already
  stops any previous watch before arming the new one (Section 3.1), so
  "watch after every successful scan" and "switching folders re-arms the
  watch" collapse into the same call. No dead comparison logic against a
  previously-watched folder is needed.

- **Clear "changes detected" on scan completion** — the spec requires
  `changes_detected_since_scan` to clear once the resulting scan completes,
  whether the scan was triggered by the manual "Scan" button or by the new
  affordance. Handled generically: `on_completed()`'s non-cancelled branch
  clears it unconditionally alongside `_set_scanned_records`, since a fresh
  successful scan makes any prior "changes detected" flag stale regardless
  of trigger source:

  ```python
  self._set_scanned_records(result.records)
  self._state = self._state.model_copy(update={"changes_detected_since_scan": False})
  ```

- **App shutdown** — the existing app-teardown path (wherever `ScanService`
  or sibling services are torn down on window close) gets one added call:
  `watch_service.stop()`. This is the same category of cleanup as any
  existing thread teardown on shutdown; no new mechanism needed, just one
  additional call alongside it.

## 5. `AppState`

`AppState` here is a plain `@dataclass` (not Pydantic) at
`src/xfinaudio/desktop/app_state.py`, already exposing a hand-written
`model_copy(update=...)` method matching the Pydantic naming convention the
proposal referenced. New field, grouped with the existing "Library / Scan"
fields:

```python
@dataclass
class AppState:
    # Library / Scan
    selected_folder: Path | None = None
    scanned_records: list[TrackRecord] = field(default_factory=list)
    records_by_path: dict[str, TrackRecord] = field(default_factory=dict)
    changes_detected_since_scan: bool = False
    ...
```

- Default `False`: matches spec's "No watch before any scan has completed"
  scenario — nothing to detect changes against yet.
- All production updates go through `state.model_copy(update={...})`
  (Sections 3.1, 4), never `state.changes_detected_since_scan = True` in
  place, per the spec's explicit `model_copy` requirement and the existing
  `AppState` convention already used by `with_screen`/`with_scanned_records`.
- No new nested model — a single `bool` field is sufficient because the spec
  only requires knowing *whether* changes were detected, not *what* changed
  (the resulting rescan re-derives everything from disk via the existing
  `scan_folder()` walk).

## 6. UI — Library screen affordance

Follows the exact `scan_button`/`cancel_button` three-part pattern already
used for every other Library-screen control: build in
`library_screen_builder.py`, signal + connect in `screens/library_screen.py`,
enable/visibility driven by `LibraryViewModel` + `LibraryScreenRenderingMixin`.

1. **`library_screen_builder.py`** — add the button next to `scan_button`/
   `cancel_button`:

   ```python
   screen.rescan_button = QPushButton(screen.tr("Changes detected — Rescan"))
   screen.rescan_button.setObjectName("secondaryAction")
   screen.rescan_button.setVisible(False)
   controls.addWidget(screen.rescan_button)
   ```

2. **`screens/library_screen.py`** —

   ```python
   rescan_requested = Signal()
   ...
   self.rescan_button.clicked.connect(self.rescan_requested)
   ...
   # in connect_signals(self, window):
   self.rescan_requested.connect(window.scan_selected_folder)
   ```

   Reusing `window.scan_selected_folder` — the exact same slot `scan_button`
   already connects to — is what keeps this "a new trigger source, not a new
   scan path" per the proposal: no new handler method, no new scan-entry
   logic, identical to a manual "Scan" click.

3. **`library_view_model.py`** — new predicate alongside
   `scan_button_enabled`/`cancel_button_visible`:

   ```python
   def rescan_button_visible(self, state: AppState) -> bool:
       """True when changes were detected and no scan is currently running."""
       return state.changes_detected_since_scan and not state.is_scanning
   ```

4. **`library_screen_rendering.py`** — one line in `render()`, alongside the
   existing `cancel_button.setVisible(...)`:

   ```python
   self.rescan_button.setVisible(vm.rescan_button_visible(state))
   ```

5. Tooltip/accessible-name entries added to `_setup_button_tooltips()` and
   `_setup_accessibility()` for consistency with every other button
   (`"Rescan the folder because files changed since the last scan"` /
   `self.tr("Rescan for detected changes")`), and to `_setup_tab_order()`
   immediately after `cancel_button`.

The `not state.is_scanning` guard in `rescan_button_visible` prevents the
affordance from being clickable while a scan is already in flight (it would
also be hidden implicitly by the watcher being paused during scans, but the
view-model guard makes the UI contract explicit and independently testable,
matching how `scan_button_enabled` already guards on `is_scanning`).

## 7. Dependency: `watchdog` version pin

Add to `pyproject.toml` `[project].dependencies`, alongside the existing
pinned entries (`mutagen>=1.47,<2.0`, `pydantic>=2.0,<3.0`, etc.):

```
"watchdog>=4.0,<7.0",
```

Rationale for the range:

- **Lower bound `4.0`**: `watchdog` 4.x is the current stable major series
  with mature FSEvents (macOS, the project's primary platform), inotify
  (Linux), and `ReadDirectoryChangesW` (Windows) backends, and ships
  `py.typed`/inline type hints — relevant to the proposal's fallback plan of
  writing "a minimal typed wrapper protocol if upstream stubs are
  insufficient." `FolderWatcher`'s `FileSystemEventSource` Protocol
  (Section 2.1) already provides that decoupling regardless of stub quality,
  so the wrapper is not a hard blocker either way.
- **Upper bound `<7.0`**: one major version of headroom past current stable,
  consistent with this project's existing pin style (e.g.
  `librosa>=0.10,<0.12`, `PySide6>=6.0,<7.0` — one arbitrary but bounded
  major/minor ceiling rather than an open-ended `>=4.0`), so a future
  breaking major release does not silently resolve into `uv.lock` without a
  deliberate bump.
- No transitive-dependency concerns: `watchdog`'s only conditional extra is
  a platform-specific backend selector it resolves internally; nothing new
  is pulled in beyond what each OS already ships.

`uv.lock` is regenerated via `uv lock` as part of implementation, per
`AGENTS.md`'s dependency-pinning convention.

## 8. Explicit non-goals (restated from spec)

Carried through design unchanged — none of the above introduces:

- **No automatic rescan.** `LibraryWatchService` only ever sets
  `changes_detected_since_scan = True` and emits `changes_detected`; nothing
  in this design calls `scan_selected_folder()` except the user clicking
  `rescan_button` (Section 6.2), which is identical to `scan_button`.
- **No DSP or audio-analysis changes.** `FolderWatcher` only forwards raw
  path/event notifications; it never opens, reads, or inspects file
  contents. The rescan triggered is the existing, unmodified
  `ScanService.scan_selected_folder()` → `scan_folder()` pipeline.
- **No audio mutation.** Nothing in `folder_watcher.py` or
  `library_watch_service.py` writes to any watched file.
- **No multi-folder / whole-library watching.** `LibraryWatchService.start()`
  always stops the previous watch before arming a new one (Section 3.1); at
  most one folder is ever watched at a time, matching `FolderWatcher`'s own
  single-`_watching_folder` state.
- **No change to `TrackRepository` cache-validity logic.** This design does
  not touch `audio_md5`/`file_mtime_ns`/`file_size_bytes` comparison logic
  anywhere; the rescan re-derives everything through the existing,
  unmodified scan/upsert path.
- **No standalone background service.** `LibraryWatchService` is a plain
  `QObject` owned by the same composition root that owns `ScanService`; its
  underlying `watchdog.Observer` thread starts in `LibraryWatchService.start()`
  and is explicitly stopped in `stop()` (app shutdown) and implicitly
  re-created per `pause()`/`resume()` cycle — it has no lifetime independent
  of the running desktop app process.

## 9. Testing strategy summary

| Layer | Test target | Seam used | Real timing/FS? |
|---|---|---|---|
| `folder_watcher.py` | `FolderWatcher.start/stop`, coalesce-free event forwarding | `FakeEventSource` (`FileSystemEventSource` Protocol) | No |
| `library_watch_service.py` | debounce/coalesce, pause/resume, single-watch invariant | `FakeEventSource` + `FakeDebounceTimer` | No |
| `library_watch_service.py` | cross-thread marshal correctness | Qt test harness (`QSignalSpy`/`qtbot`, consistent with existing Qt-slot tests in this codebase) | No (signal delivery is synchronous enough under `qtbot.waitSignal` without real filesystem timing) |
| `scan_service.py` integration | pause called in `begin_scan_state`, resume/start/clear called in `_end_scan_state`/`on_completed` | Fake `LibraryWatchService` (spy) injected via `set_watch_service` | No |
| Library screen | `rescan_button` visibility, click → `scan_selected_folder` | `LibraryViewModel`/`AppState` fixtures, existing `qtbot` click pattern | No |
| End-to-end (optional, marked slow/integration) | real `watchdog` observer against a temp dir | Real filesystem, real `watchdog` | Yes — kept minimal and separate from the RED-phase unit suite |

Every debounce/coalesce/lifecycle test runs against the injected seams
(`FileSystemEventSource`, `DebounceTimer`) so RED-phase tests are
deterministic and fast; only a small, explicitly-marked integration test (if
added at all) touches real `watchdog`/filesystem timing, isolated from the
rest of the suite.
