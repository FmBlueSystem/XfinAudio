"""Real shell preview interactions with a non-playing synthetic player."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QMediaPlayer
from shiboken6 import isValid

from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop import window_factory
from xfinaudio.desktop.audio_player import AudioPlayer
from xfinaudio.desktop.audio_player_state import PlayerState, PlayerStateMachine
from xfinaudio.desktop.library_columns import column_index
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord


class FakePlayer(QObject):
    state_changed = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source_path: str | None = None
        self.state = PlayerState.IDLE
        self.calls: list[str] = []
        self.position = 12345

    def set_volume(self, _volume: float) -> None:
        pass

    def _set_state(self, state: PlayerState) -> None:
        self.state = state
        self.state_changed.emit(state)

    def stop(self) -> None:
        self.calls.append("stop")
        self._set_state(PlayerState.IDLE)

    def load(self, path: str) -> None:
        self.calls.append("load")
        self._source_path = path
        self._set_state(PlayerState.LOADING)
        self._set_state(PlayerState.PLAYING)

    def pause(self) -> None:
        self.calls.append("pause")
        self._set_state(PlayerState.PAUSED)

    def play(self) -> None:
        self.calls.append("resume")
        self._set_state(PlayerState.PLAYING)

    def shutdown(self) -> None:
        self.stop()


@pytest.fixture
def preview_window(qapp, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(window_factory, "AudioPlayer", FakePlayer)
    monkeypatch.setattr(window_factory, "create_loudness_completion_service", lambda: None)
    repository: Any = Mock(db_path=tmp_path / "library.sqlite3")
    repository.list_display_tracks.return_value = []
    window = MainWindow(scan_service=Mock(), repository=repository, settings=AppSettings())
    monkeypatch.setattr(window._library_controller, "start_spectral_completion_worker", lambda _records: None)
    window.show_tracks(
        [
            TrackRecord(
                path=str(tmp_path / "synthetic-not-opened.flac"),
                title="Synthetic preview",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
        ]
    )
    window._library_screen.tracks_table.selectRow(0)
    yield window
    window.close()
    qapp.processEvents()


def test_first_play_after_show_tracks_keeps_items_selection_and_playback(preview_window: MainWindow) -> None:
    screen = preview_window._library_screen
    table = screen.tracks_table
    assert screen._last_rows_signature is None  # Actual direct-population route.
    items = [table.item(0, column) for column in range(table.columnCount())]
    selected = list(preview_window._library_selected_paths)
    assert len(selected) == 1
    table.cellClicked.emit(0, column_index("Preview"))
    preview_window._sync_state()

    assert preview_window._audio_player.state is PlayerState.PLAYING
    assert preview_window._audio_player.calls == ["stop", "load"]
    assert screen._last_rows_signature is None
    assert all(isValid(item) and item is table.item(0, column) for column, item in enumerate(items))
    assert preview_window._library_selected_paths == selected
    assert table.item(0, column_index("Preview")).text() == "⏸"


def test_three_preview_clicks_resume_without_reload(preview_window: MainWindow) -> None:
    table = preview_window._library_screen.tracks_table
    player = preview_window._audio_player
    table.cellClicked.emit(0, column_index("Preview"))
    player.position = 12345
    table.cellClicked.emit(0, column_index("Preview"))
    assert player.state is PlayerState.PAUSED
    assert table.item(0, column_index("Preview")).text() == "▶"
    table.cellClicked.emit(0, column_index("Preview"))
    assert player.state is PlayerState.PLAYING
    assert player.calls == ["stop", "load", "pause", "resume"]
    assert player.position == 12345
    assert table.item(0, column_index("Preview")).text() == "⏸"


def test_player_accepts_qt_playing_callback_after_pause() -> None:
    machine = PlayerStateMachine()
    for event in ("load", "play", "pause"):
        machine.transition(event)
    owner: Any = SimpleNamespace(_state_machine=machine)
    AudioPlayer._on_playback_state_changed(owner, QMediaPlayer.PlaybackState.PlayingState)
    assert machine.state is PlayerState.PLAYING


def test_sort_restores_only_final_selection_without_stopping_preview(preview_window: MainWindow) -> None:
    screen = preview_window._library_screen
    table = screen.tracks_table
    player = preview_window._audio_player
    table.cellClicked.emit(0, column_index("Preview"))
    selected = list(preview_window._library_selected_paths)
    changes: list[list[str]] = []
    screen.selection_changed.connect(changes.append)
    table.horizontalHeader().sectionDoubleClicked.emit(column_index("Title"))

    assert player.state is PlayerState.PLAYING
    assert player.calls == ["stop", "load"]
    assert preview_window._library_selected_paths == selected
    assert [] not in changes


def test_filter_removing_playing_row_publishes_empty_selection_and_stops(preview_window: MainWindow) -> None:
    screen = preview_window._library_screen
    screen.tracks_table.cellClicked.emit(0, column_index("Preview"))
    screen.incomplete_filter_button.click()

    assert screen.tracks_table.rowCount() == 0
    assert preview_window._library_selected_paths == []
    assert preview_window._audio_player.state is PlayerState.IDLE
    assert screen._playing_path is None
