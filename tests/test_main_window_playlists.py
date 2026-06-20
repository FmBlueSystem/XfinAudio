"""Tests for MainWindow playlist integration."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


class FakeScanService:
    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        return []


class FakeRepository:
    def __init__(self) -> None:
        self.db_path = Path(tempfile.mkdtemp()) / "tracks.db"

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


def _recommendation() -> PlaylistRecommendation:
    tracks = [TrackRecord(path="/music/a.flac", title="A", metadata_status="complete")]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


class TestPlaylistRepository:
    def test_main_window_creates_playlist_repository(self, qapp: QApplication) -> None:
        window = make_window()
        assert window._playlist_repository is not None

    def test_my_playlists_tab_exists(self, qapp: QApplication) -> None:
        window = make_window()
        tabs = [window.workflow_tabs.tabText(i) for i in range(window.workflow_tabs.count())]
        assert "My Playlists" in tabs

    def test_review_save_button_persists_recommendation_and_switches_to_my_playlists(self, qapp: QApplication) -> None:
        window = make_window()
        window.last_recommendation = _recommendation()
        window._sync_state()

        window._review_screen.save_to_playlists_button.click()

        saved = window._playlist_repository.list_summaries()
        assert len(saved) == 1
        assert saved[0].track_count == 1
        assert saved[0].name.startswith("build - ")
        assert window.workflow_tabs.currentIndex() == 4
        assert window._playlists_screen.list_widget.count() == 1
