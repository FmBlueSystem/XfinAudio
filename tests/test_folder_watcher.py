"""Tests for the FolderWatcher library-layer abstraction (fake event source)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from xfinaudio.library.folder_watcher import FolderWatcher


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
        """Synchronously invoke the captured on_raw_event callback, if any."""
        if self._on_raw_event is not None:
            self._on_raw_event(path)


def test_start_arms_watch_on_folder() -> None:
    event_source = FakeEventSource()
    watcher = FolderWatcher(event_source=event_source)
    folder = Path("/tmp/library")

    watcher.start(folder, on_event=lambda path: None)

    assert event_source.start_calls == [folder]
    assert watcher.is_watching is True


def test_stop_stops_watch() -> None:
    event_source = FakeEventSource()
    watcher = FolderWatcher(event_source=event_source)
    watcher.start(Path("/tmp/library"), on_event=lambda path: None)

    watcher.stop()

    assert event_source.stop_calls == 1
    assert watcher.is_watching is False


def test_stop_is_noop_when_not_watching() -> None:
    event_source = FakeEventSource()
    watcher = FolderWatcher(event_source=event_source)

    watcher.stop()

    assert event_source.stop_calls == 0
    assert watcher.is_watching is False


def test_start_replaces_previous_watch() -> None:
    event_source = FakeEventSource()
    watcher = FolderWatcher(event_source=event_source)
    watcher.start(Path("/tmp/library-a"), on_event=lambda path: None)

    watcher.start(Path("/tmp/library-b"), on_event=lambda path: None)

    assert event_source.stop_calls == 1
    assert event_source.start_calls == [Path("/tmp/library-a"), Path("/tmp/library-b")]
    assert watcher.is_watching is True


def test_event_before_start_never_fires() -> None:
    event_source = FakeEventSource()
    watcher = FolderWatcher(event_source=event_source)

    event_source.fire("/tmp/library/track.mp3")  # no-op: callback never registered

    assert watcher.is_watching is False
