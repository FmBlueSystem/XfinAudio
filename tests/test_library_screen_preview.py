"""Tests for LibraryScreen preview column integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.screens.library_screen import LibraryScreen
from xfinaudio.library.models import TrackRecord


def make_track(path: str = "/library/track.mp3", title: str = "Test Track") -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist="Test Artist",
        bpm=128.0,
        camelot_key="8A",
        energy_level=7,
        genre="House",
        metadata_status="complete",
        missing_required_fields=[],
    )


def make_state(tracks: list[TrackRecord]) -> AppState:
    state = AppState()
    state = state.with_scanned_records(tracks)
    state.selected_folder = Path("/library")
    return state


class TestPreviewColumn:
    def test_has_preview_column(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        headers = [screen.tracks_table.horizontalHeaderItem(i).text() for i in range(screen.tracks_table.columnCount())]
        assert "Preview" in headers

    def test_preview_column_has_play_buttons(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3")])
        screen.render(vm, state)
        preview_col = _preview_column_index(screen)
        item = screen.tracks_table.item(0, preview_col)
        assert item is not None
        assert item.text() == "▶"


class TestPlayRequested:
    def test_click_preview_emits_play_requested(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        paths: list[str] = []
        screen.play_requested.connect(paths.append)
        preview_col = _preview_column_index(screen)
        screen._on_cell_clicked(0, preview_col)
        assert len(paths) == 1
        assert paths[0] == "/library/a.mp3"

    def test_click_non_preview_does_not_emit(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        paths: list[str] = []
        screen.play_requested.connect(paths.append)
        screen._on_cell_clicked(0, 0)  # Title column
        assert paths == []


class TestPreviewWithoutPath:
    def test_click_preview_with_missing_path_item_emits_guidance_signal(self, qapp: QApplication) -> None:
        """A Preview click on a row whose Path item is gone must report, not fail silently."""
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        preview_col = _preview_column_index(screen)
        path_col = screen.tracks_table.columnCount() - 1  # Path is the last column
        screen.tracks_table.takeItem(0, path_col)
        requests: list[None] = []
        screen.preview_without_path_requested.connect(lambda: requests.append(None))
        screen._on_cell_clicked(0, preview_col)
        assert requests == [None]

    def test_missing_path_guidance_reaches_status_label(self, qapp: QApplication) -> None:
        """The screen signal must be wired to the window status surface."""
        screen = LibraryScreen()
        window = Mock()
        screen.connect_signals(window)
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        preview_col = _preview_column_index(screen)
        path_col = screen.tracks_table.columnCount() - 1
        screen.tracks_table.takeItem(0, path_col)
        screen._on_cell_clicked(0, preview_col)
        window.status_label.setText.assert_called_once_with("Select a complete track to preview")


class TestPauseRequested:
    def test_click_preview_when_playing_emits_pause(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        pauses: list[None] = []
        screen.pause_requested.connect(lambda: pauses.append(None))
        screen.set_playing_row("/library/a.mp3")
        preview_col = _preview_column_index(screen)
        screen._on_cell_clicked(0, preview_col)
        assert len(pauses) == 1


class TestSetPlayingRow:
    def test_set_playing_row_updates_preview_text(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        preview_col = _preview_column_index(screen)
        screen.set_playing_row("/library/a.mp3")
        item = screen.tracks_table.item(0, preview_col)
        assert item is not None
        assert item.text() == "⏸"

    def test_set_playing_row_none_resets_preview_text(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        preview_col = _preview_column_index(screen)
        screen.set_playing_row("/library/a.mp3")
        screen.set_playing_row(None)
        item = screen.tracks_table.item(0, preview_col)
        assert item is not None
        assert item.text() == "▶"

    def test_set_playing_row_highlight(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        screen.set_playing_row("/library/a.mp3")
        preview_col = _preview_column_index(screen)
        item = screen.tracks_table.item(0, preview_col)
        assert item is not None
        assert item.background().color().name() == "#5a4be0"

    def test_set_playing_row_for_missing_path_is_noop(self, qapp: QApplication) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = make_state([make_track("/library/a.mp3", "Track A")])
        screen.render(vm, state)
        screen.set_playing_row("/library/nonexistent.mp3")
        preview_col = _preview_column_index(screen)
        item = screen.tracks_table.item(0, preview_col)
        assert item is not None
        assert item.text() == "▶"


def _preview_column_index(screen: LibraryScreen) -> int:
    for i in range(screen.tracks_table.columnCount()):
        header = screen.tracks_table.horizontalHeaderItem(i)
        if header is not None and header.text() == "Preview":
            return i
    raise RuntimeError("Preview column not found")
