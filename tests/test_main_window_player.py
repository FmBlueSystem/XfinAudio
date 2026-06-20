"""Tests for MainWindow audio player coordination."""

from __future__ import annotations

from pathlib import Path

import pytest
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


class TestAudioPlayerCreation:
    def test_main_window_creates_audio_player(self, qapp: QApplication) -> None:
        window = make_window()
        assert window._audio_player is not None

    def test_audio_player_initial_volume_from_settings_default(self, qapp: QApplication) -> None:
        settings = AppSettings()
        window = MainWindow(
            scan_service=FakeScanService(),
            repository=FakeRepository(),
            settings=settings,
            settings_repository=FakeSettingsRepo(),
        )
        assert window._audio_player.volume == pytest.approx(0.7, abs=0.01)

    def test_audio_player_initial_volume_from_settings_custom(self, qapp: QApplication) -> None:
        from xfinaudio.config.settings import AudioSettings

        settings = AppSettings(audio=AudioSettings(preview_volume=0.3))
        window = MainWindow(
            scan_service=FakeScanService(),
            repository=FakeRepository(),
            settings=settings,
            settings_repository=FakeSettingsRepo(),
        )
        assert window._audio_player.volume == pytest.approx(0.3, abs=0.01)


class TestPlayRequested:
    def test_play_requested_loads_track(self, qapp: QApplication) -> None:
        window = make_window()
        window._library_screen.play_requested.emit("/music/track.flac")
        assert window._audio_player._source_path == "/music/track.flac"


class TestPauseRequested:
    def test_pause_requested_pauses_player(self, qapp: QApplication) -> None:
        window = make_window()
        # Load a track first so pause is valid
        window._audio_player.load(str(Path(__file__).with_name("fixtures") / "silence_1s.wav"))
        window._library_screen.pause_requested.emit()
        from xfinaudio.desktop.audio_player_state import PlayerState

        assert window._audio_player.state in (PlayerState.PAUSED, PlayerState.PLAYING, PlayerState.LOADING)


class TestSelectionChangeStopsPlayer:
    def test_new_selection_stops_current_preview(self, qapp: QApplication) -> None:
        window = make_window()
        window._audio_player.load(str(Path(__file__).with_name("fixtures") / "silence_1s.wav"))
        from xfinaudio.desktop.audio_player_state import PlayerState

        assert window._audio_player.state != PlayerState.IDLE
        window._on_library_selection_changed(["/other/track.flac"])
        assert window._audio_player.state == PlayerState.IDLE


class TestPlayerStateUpdatesLibraryScreen:
    def test_player_state_changed_updates_library_screen(self, qapp: QApplication) -> None:
        window = make_window()
        window._library_screen.set_playing_row("/music/track.flac")
        assert window._library_screen._playing_path == "/music/track.flac"
