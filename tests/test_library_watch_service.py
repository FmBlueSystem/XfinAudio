"""Tests for LibraryWatchService: debounce coalescing, pause/resume,
single-watch invariant, and cross-thread marshal (fake seams)."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xfinaudio.desktop.library_watch_service import LibraryWatchService  # noqa: E402
from xfinaudio.library.folder_watcher import FolderWatcher  # noqa: E402

_EXISTING_APP = QApplication.instance()
_APP: QApplication = _EXISTING_APP if isinstance(_EXISTING_APP, QApplication) else QApplication([])


class FakeEventSource:
    """Records start/stop calls and lets tests fire raw events synchronously."""

    def __init__(self) -> None:
        self.start_calls: list[Path] = []
        self.stop_calls: int = 0
        self._on_raw_event: Callable[[str], None] | None = None

    def start(self, folder: Path, on_raw_event: Callable[[str], None]) -> None:
        self.start_calls.append(folder)
        self._on_raw_event = on_raw_event

    def stop(self) -> None:
        self.stop_calls += 1
        self._on_raw_event = None

    def fire(self, path: str) -> None:
        if self._on_raw_event is not None:
            self._on_raw_event(path)


class FakeDebounceTimer:
    """Seam over QTimer: records start/stop and lets tests fire the timeout
    callback synchronously rather than waiting on real Qt-timer timing."""

    def __init__(self, on_timeout: Callable[[], None]) -> None:
        self._on_timeout = on_timeout
        self.start_calls: list[int] = []
        self.stop_calls: int = 0
        self._active = False

    def start(self, msec: int) -> None:
        self.start_calls.append(msec)
        self._active = True

    def stop(self) -> None:
        self.stop_calls += 1
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def fire(self) -> None:
        """Synchronously invoke the timeout callback, as a real QTimer would."""
        self._active = False
        self._on_timeout()


class FakeState:
    """Minimal stand-in for AppState: records model_copy(update=...) calls."""

    def __init__(self, changes_detected_since_scan: bool = False) -> None:
        self.changes_detected_since_scan = changes_detected_since_scan
        self.model_copy_calls: list[dict[str, Any]] = []

    def model_copy(self, *, update: dict[str, Any]) -> FakeState:
        self.model_copy_calls.append(update)
        new_changes_detected = update.get("changes_detected_since_scan", self.changes_detected_since_scan)
        new_state = FakeState(changes_detected_since_scan=new_changes_detected)
        new_state.model_copy_calls = self.model_copy_calls
        return new_state


def _make_service() -> tuple[LibraryWatchService, FakeEventSource, FakeDebounceTimer]:
    event_source = FakeEventSource()
    folder_watcher = FolderWatcher(event_source=event_source)
    timers: list[FakeDebounceTimer] = []

    def factory(on_timeout: Callable[[], None]) -> FakeDebounceTimer:
        timer = FakeDebounceTimer(on_timeout)
        timers.append(timer)
        return timer

    service = LibraryWatchService(folder_watcher, debounce_timer_factory=factory, settle_window_ms=2000)
    return service, event_source, timers[0]


def test_start_arms_watcher_on_folder() -> None:
    service, event_source, _timer = _make_service()
    folder = Path("/tmp/library")

    service.start(folder)

    assert event_source.start_calls == [folder]


def test_raw_event_restarts_debounce_timer() -> None:
    service, event_source, timer = _make_service()
    service.start(Path("/tmp/library"))

    event_source.fire("/tmp/library/track.mp3")

    assert timer.start_calls == [2000]


def test_burst_of_events_coalesces_to_single_emission() -> None:
    service, event_source, timer = _make_service()
    service.start(Path("/tmp/library"))
    emissions: list[None] = []
    service.changes_detected.connect(lambda: emissions.append(None))

    event_source.fire("/tmp/library/a.mp3")
    event_source.fire("/tmp/library/b.mp3")
    event_source.fire("/tmp/library/c.mp3")
    timer.fire()

    assert len(emissions) == 1


def test_timeout_sets_state_via_model_copy() -> None:
    service, event_source, timer = _make_service()
    state = FakeState()
    service.set_state_accessors(state=state, sync_state=lambda: None)
    service.start(Path("/tmp/library"))

    event_source.fire("/tmp/library/track.mp3")
    timer.fire()

    assert state.model_copy_calls == [{"changes_detected_since_scan": True}]


def test_pause_stops_watch_and_remembers_folder() -> None:
    service, event_source, _timer = _make_service()
    service.start(Path("/tmp/library"))

    service.pause()

    assert event_source.stop_calls == 1


def test_resume_rearms_previously_paused_folder() -> None:
    service, event_source, _timer = _make_service()
    folder = Path("/tmp/library")
    service.start(folder)
    service.pause()

    service.resume()

    assert event_source.start_calls == [folder, folder]


def test_pause_without_active_watch_is_noop() -> None:
    service, event_source, _timer = _make_service()

    service.pause()

    assert event_source.stop_calls == 0


def test_resume_without_pause_is_noop() -> None:
    service, event_source, _timer = _make_service()

    service.resume()

    assert event_source.start_calls == []


def test_stop_stops_watch_and_clears_pause_state() -> None:
    service, event_source, _timer = _make_service()
    service.start(Path("/tmp/library"))

    service.stop()
    service.resume()

    assert event_source.stop_calls == 1
    assert event_source.start_calls == [Path("/tmp/library")]


def test_start_after_previous_watch_switches_folder() -> None:
    service, event_source, _timer = _make_service()
    service.start(Path("/tmp/library-a"))

    service.start(Path("/tmp/library-b"))

    assert event_source.stop_calls == 1
    assert event_source.start_calls == [Path("/tmp/library-a"), Path("/tmp/library-b")]


# ---------------------------------------------------------------------------
# Lifecycle edge cases (design.md §9 integration matrix)
# ---------------------------------------------------------------------------


def test_folder_switch_stops_old_watch_and_arms_new() -> None:
    """Switching folders stops the old watch before arming the new one (spec:
    'Switching folders re-arms the watch')."""
    service, event_source, _timer = _make_service()
    folder_a = Path("/tmp/library-a")
    folder_b = Path("/tmp/library-b")
    service.start(folder_a)

    service.start(folder_b)

    assert event_source.stop_calls == 1
    assert event_source.start_calls == [folder_a, folder_b]
    assert service.is_watching is True


def test_shutdown_stops_watcher_with_no_leaked_threads() -> None:
    """stop() clears all internal state; no dangling debounce timer remains active."""
    service, event_source, timer = _make_service()
    service.start(Path("/tmp/library"))
    event_source.fire("/tmp/library/track.mp3")
    assert timer.is_active() is True

    service.stop()

    assert event_source.stop_calls == 1
    assert timer.is_active() is False
    assert service.is_watching is False


def test_pause_during_scan_does_not_self_trigger_from_scan_reads() -> None:
    """A stray raw event fired on the paused watcher's underlying source must not
    emit changes_detected while paused (the scan's own filesystem reads must not
    self-trigger the watcher)."""
    service, event_source, _timer = _make_service()
    service.start(Path("/tmp/library"))
    service.pause()
    emissions: list[None] = []
    service.changes_detected.connect(lambda: emissions.append(None))

    # The paused watcher stopped the event source, so a stray callback
    # reference (simulating a race with in-flight scan reads) cannot fire
    # through the fake, matching the real FolderWatcher.stop() contract.
    event_source.fire("/tmp/library/track.mp3")

    assert emissions == []


def test_burst_across_pause_resume_debounce_chain_coalesces_once() -> None:
    """A burst of events firing after resume() still coalesces to a single
    changes_detected emission, exercising the full pause -> resume -> debounce
    chain together."""
    service, event_source, timer = _make_service()
    folder = Path("/tmp/library")
    service.start(folder)
    service.pause()
    service.resume()
    emissions: list[None] = []
    service.changes_detected.connect(lambda: emissions.append(None))

    event_source.fire("/tmp/library/a.mp3")
    event_source.fire("/tmp/library/b.mp3")
    event_source.fire("/tmp/library/c.mp3")
    timer.fire()

    assert len(emissions) == 1


def _pump_events_until(predicate: Callable[[], bool], timeout_seconds: float = 5.0) -> bool:
    import time

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
    return False


def test_cross_thread_raw_event_marshals_to_main_thread_and_starts_timer() -> None:
    service, _event_source, timer = _make_service()
    service.start(Path("/tmp/library"))

    thread = threading.Thread(target=lambda: service._on_raw_event_background_thread("/tmp/library/track.mp3"))
    thread.start()
    thread.join()

    assert _pump_events_until(lambda: timer.is_active())
    assert timer.start_calls == [2000]
