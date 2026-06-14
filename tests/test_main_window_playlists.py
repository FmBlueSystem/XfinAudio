"""Tests for MainWindow playlist integration."""

from __future__ import annotations

from pathlib import Path

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
    def save(self, settings: AppSettings) -> None:
        pass


def make_window() -> MainWindow:
    return MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings=AppSettings(),
        settings_repository=FakeSettingsRepo(),
    )


class TestPlaylistRepository:
    def test_main_window_creates_playlist_repository(self, qapp: QApplication) -> None:
        window = make_window()
        assert window._playlist_repository is not None

    def test_my_playlists_tab_exists(self, qapp: QApplication) -> None:
        window = make_window()
        tabs = [window.workflow_tabs.tabText(i) for i in range(window.workflow_tabs.count())]
        assert "My Playlists" in tabs
