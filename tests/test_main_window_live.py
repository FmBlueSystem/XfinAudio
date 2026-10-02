"""Tests for MainWindow Live Assistant integration."""

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord


class _FakeScanService:
    def scan(self, folder, **kwargs):
        return []


class _FakeRepository:
    def save_scan_results(self, records, *, pruned_root=None):
        pass


def make_window() -> MainWindow:
    return MainWindow(
        scan_service=_FakeScanService(),
        repository=_FakeRepository(),
    )


def test_live_assistant_tab_exists(qapp: QApplication) -> None:
    window = make_window()
    tab_names = [window.workflow_tabs.tabText(i) for i in range(window.workflow_tabs.count())]
    assert "Live Assistant" in tab_names


def test_live_assistant_keeps_stable_tab_index(qapp: QApplication) -> None:
    window = make_window()
    assert window.workflow_tabs.tabText(6) == "Live Assistant"


def test_exit_live_assistant_navigates_to_library(qapp: QApplication) -> None:
    window = make_window()
    window.workflow_tabs.setCurrentIndex(6)
    window._live_assistant_screen.exit_requested.emit()
    assert window.workflow_tabs.currentIndex() == 0


def test_preview_from_live_assistant_uses_audio_player(qapp: QApplication) -> None:
    window = make_window()
    track = TrackRecord(
        path="/a.flac",
        title="A",
        artist="Artist",
        bpm=128.0,
        camelot_key="11B",
        energy_level=7,
        metadata_status="complete",
    )
    window._live_assistant_screen.preview_requested.emit(track.path)
    # Should not crash; single-player coordination handles it
    assert window._audio_player is not None
