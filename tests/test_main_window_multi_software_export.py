"""Tests for MainWindow multi-software export integration."""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


class _FakeScanService:
    def scan(self, folder, **kwargs):
        return []


class _FakeRepository:
    def save_scan_results(self, records):
        pass


def _make_recommendation(paths: list[str]) -> PlaylistRecommendation:
    tracks = [
        TrackRecord(
            path=path,
            title=Path(path).stem,
            artist="Artist",
            bpm=128.0,
            camelot_key="11B",
            energy_level=7,
            metadata_status="complete",
        )
        for path in paths
    ]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def make_window() -> MainWindow:
    return MainWindow(
        scan_service=_FakeScanService(),
        repository=_FakeRepository(),
    )


def test_main_window_has_software_selector(qapp: QApplication) -> None:
    window = make_window()
    assert window._export_screen.software_selector is not None


def test_main_window_export_button_reflects_software(qapp: QApplication) -> None:
    window = make_window()
    window._export_screen.software_selector.setCurrentText("Rekordbox")
    assert "Rekordbox" in window._export_screen.export_button.text()


def test_main_window_routes_rekordbox_export(qapp: QApplication, tmp_path: Path) -> None:
    from xfinaudio.config.settings import ExportSettings

    window = make_window()
    window.settings = window.settings.model_copy(update={"export": ExportSettings(safe_export_folder=tmp_path)})
    track_path = str(tmp_path / "track1.flac")
    window.last_recommendation = _make_recommendation([track_path])
    window._export_screen.software_selector.setCurrentText("Rekordbox")
    window.export_recommendation(serato_folder=tmp_path, crate_name="Test")
    exported = list(tmp_path.glob("*.xml"))
    assert len(exported) == 1
