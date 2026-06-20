"""Tests for audio preview error handling and keyboard shortcuts."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord


class FakeScanService:
    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        return []


class FakeRepository:
    def save_scan_results(self, records: list[TrackRecord]) -> None:
        pass

    def list_display_tracks(self) -> list[TrackRecord]:
        return []


class FakeSettingsRepo:
    def load(self) -> AppSettings:
        return AppSettings()

    def save(self, settings: AppSettings) -> None:
        pass


def make_window() -> MainWindow:
    return MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings=AppSettings(),
        settings_repository=FakeSettingsRepo(),
    )


class TestErrorHandling:
    def test_player_error_clears_playing_row(self, qapp: QApplication) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        window = make_window()
        fixture = str(Path(__file__).with_name("fixtures") / "silence_1s.wav")
        window._audio_player.load(fixture)
        window._audio_player._on_player_error(QMediaPlayer.Error.ResourceError, "not found")
        assert window._library_screen._playing_path is None


class TestKeyboardShortcut:
    def test_space_shortcut_toggles_play_pause(self, qapp: QApplication) -> None:
        window = make_window()
        # Focus the library table
        window._library_screen.tracks_table.setFocus()
        # Simulate space key press
        from PySide6.QtGui import QKeyEvent

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
        window._library_screen.keyPressEvent(event)
        # No crash is the minimal assertion for now
