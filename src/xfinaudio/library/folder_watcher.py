"""App-owned abstraction over watchdog's Observer, decoupled from its types."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class FileSystemEventSource(Protocol):
    """Seam: anything that can start/stop watching a folder and report raw
    create/modify/delete events for paths under it. watchdog's Observer
    satisfies this at runtime; tests substitute a fake."""

    def start(self, folder: Path, on_raw_event: Callable[[str], None]) -> None: ...

    def stop(self) -> None: ...


class _ForwardingEventHandler(FileSystemEventHandler):
    """Forwards every raw watchdog event to a plain callback, unfiltered."""

    def __init__(self, on_raw_event: Callable[[str], None]) -> None:
        super().__init__()
        self._on_raw_event = on_raw_event

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._on_raw_event(str(event.src_path))


class WatchdogEventSource:
    """Real implementation: wraps watchdog.observers.Observer +
    watchdog.events.FileSystemEventHandler. The only module that imports
    `watchdog` directly."""

    def __init__(self) -> None:
        self._observer: Any | None = None

    def start(self, folder: Path, on_raw_event: Callable[[str], None]) -> None:
        observer = Observer()
        handler = _ForwardingEventHandler(on_raw_event)
        observer.schedule(handler, str(folder), recursive=True)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None


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


__all__ = ["FileSystemEventSource", "FolderWatcher", "WatchdogEventSource"]
