"""Qt lifecycle owner for filesystem-change detection on the scanned folder."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from xfinaudio.library.folder_watcher import FolderWatcher


def _unwired(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError("LibraryWatchService dependencies were not wired")


class DebounceTimer(Protocol):
    """Seam over QTimer so tests can trigger a timeout deterministically."""

    def start(self, msec: int) -> None: ...

    def stop(self) -> None: ...

    def is_active(self) -> bool: ...


class _QTimerAdapter:
    """Real DebounceTimer implementation backed by a singleShot QTimer."""

    def __init__(self, on_timeout: Callable[[], None]) -> None:
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(on_timeout)

    def start(self, msec: int) -> None:
        self._timer.start(msec)

    def stop(self) -> None:
        self._timer.stop()

    def is_active(self) -> bool:
        return self._timer.isActive()


def _qtimer_factory(on_timeout: Callable[[], None]) -> DebounceTimer:
    return _QTimerAdapter(on_timeout)


class LibraryWatchService(QObject):
    """Qt-thread-safe lifecycle owner for filesystem-change detection."""

    changes_detected = Signal()
    _raw_event_received = Signal(str)  # internal cross-thread marshal

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
        self._paused_folder: Path | None = None
        self._state: Any = None
        self._sync_state: Callable[[], None] = _unwired

        self._raw_event_received.connect(self._on_raw_event_main_thread)

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

    @property
    def is_watching(self) -> bool:
        return self._watched_folder is not None

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
            self._sync_state()
        self.changes_detected.emit()


__all__ = ["DebounceTimer", "LibraryWatchService"]
