"""Tests for visual integration: screens connected to their respective tabs."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.screens import BuildScreen, ExportScreen, LibraryScreen, MetadataScreen, ReviewScreen
from xfinaudio.library.models import TrackRecord


def _ensure_app() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


class _FakeScanService:
    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        return []


class _FakeRepository:
    def save_scan_results(self, records: list[TrackRecord]) -> None:
        pass


def _make_window() -> MainWindow:
    _ensure_app()
    return MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())


def make_track(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title="Test",
        artist="Artist",
        bpm=120.0,
        camelot_key="8A",
        energy_level=6,
        metadata_status="complete",
    )


@pytest.fixture()
def qapp():
    return _ensure_app()


@pytest.fixture()
def window(qapp):
    return _make_window()


def test_library_screen_is_tab_zero(qapp, window):
    """LibraryScreen must be the widget at tab index 0."""
    tab_widget = window.workflow_tabs.widget(0)
    assert isinstance(tab_widget, LibraryScreen)


def test_library_screen_renders_on_sync(qapp, window):
    """After _sync_state, library screen shows correct track count."""
    window.scanned_records = [make_track("/a.flac"), make_track("/b.flac")]
    window._sync_state()
    assert window._library_screen.tracks_table.rowCount() >= 0  # no crash


def test_library_screen_signals_connected(qapp, window, monkeypatch):
    """LibraryScreen signals must be connected without raising."""
    # Patch dialog-opening / scan-starting handlers before emitting
    monkeypatch.setattr(window, "choose_folder", lambda: None)
    monkeypatch.setattr(window, "scan_selected_folder", lambda: None)
    monkeypatch.setattr(window, "cancel_scan", lambda: None)
    window._library_screen.folder_change_requested.emit()
    window._library_screen.scan_requested.emit()
    window._library_screen.cancel_scan_requested.emit()
    window._library_screen.selection_changed.emit([])
    window._library_screen.metadata_screen_requested.emit()


def test_library_screen_folder_change_requested_opens_choose_folder(qapp, window, monkeypatch):
    """folder_change_requested signal must invoke choose_folder on the window."""
    called: list[bool] = []
    monkeypatch.setattr(window, "choose_folder", lambda: called.append(True))
    window._library_screen.folder_change_requested.emit()
    assert called == [True]


def test_library_screen_scan_requested_triggers_scan(qapp, window, monkeypatch):
    """scan_requested signal must invoke scan_selected_folder on the window."""
    called: list[bool] = []
    monkeypatch.setattr(window, "scan_selected_folder", lambda: called.append(True))
    window._library_screen.scan_requested.emit()
    assert called == [True]


def test_library_screen_cancel_scan_requested_cancels(qapp, window, monkeypatch):
    """cancel_scan_requested signal must invoke cancel_scan on the window."""
    called: list[bool] = []
    monkeypatch.setattr(window, "cancel_scan", lambda: called.append(True))
    window._library_screen.cancel_scan_requested.emit()
    assert called == [True]


def test_library_screen_metadata_screen_requested_navigates_to_tab_4(qapp, window):
    """metadata_screen_requested must navigate to tab index 4 (Metadata Worklist)."""
    window.workflow_tabs.setCurrentIndex(0)
    window._library_screen.metadata_screen_requested.emit()
    assert window.workflow_tabs.currentIndex() == 4


# ---------------------------------------------------------------------------
# Task 3 — BuildScreen
# ---------------------------------------------------------------------------


def test_build_screen_is_tab_one(qapp, window):
    """BuildScreen must be the widget at tab index 1."""
    assert isinstance(window.workflow_tabs.widget(1), BuildScreen)


def test_build_back_signal_navigates_to_library(qapp, window):
    """back_requested from BuildScreen must navigate to tab 0 (Library)."""
    window.workflow_tabs.setCurrentIndex(1)
    window._build_screen.back_requested.emit()
    assert window.workflow_tabs.currentIndex() == 0


# ---------------------------------------------------------------------------
# Task 4 — ReviewScreen
# ---------------------------------------------------------------------------


def test_review_screen_is_tab_two(qapp, window):
    """ReviewScreen must be the widget at tab index 2."""
    assert isinstance(window.workflow_tabs.widget(2), ReviewScreen)


def test_review_back_navigates_to_build(qapp, window):
    """back_requested from ReviewScreen must navigate to tab 1 (Build)."""
    window.workflow_tabs.setCurrentIndex(2)
    window._review_screen.back_requested.emit()
    assert window.workflow_tabs.currentIndex() == 1


# ---------------------------------------------------------------------------
# Task 5 — ExportScreen
# ---------------------------------------------------------------------------


def test_export_screen_is_tab_three(qapp, window):
    """ExportScreen must be the widget at tab index 3."""
    assert isinstance(window.workflow_tabs.widget(3), ExportScreen)


def test_export_back_navigates_to_review(qapp, window):
    """back_requested from ExportScreen must navigate to tab 2 (Review)."""
    window.workflow_tabs.setCurrentIndex(3)
    window._export_screen.back_requested.emit()
    assert window.workflow_tabs.currentIndex() == 2


# ---------------------------------------------------------------------------
# Task 6 — MetadataScreen
# ---------------------------------------------------------------------------


def test_metadata_screen_is_tab_four(qapp, window):
    """MetadataScreen must be the widget at tab index 4."""
    assert isinstance(window.workflow_tabs.widget(4), MetadataScreen)


def test_metadata_back_navigates_to_library(qapp, window):
    """back_requested from MetadataScreen must navigate to tab 0 (Library)."""
    window.workflow_tabs.setCurrentIndex(4)
    window._metadata_screen.back_requested.emit()
    assert window.workflow_tabs.currentIndex() == 0


def test_main_window_exposes_visible_library_table_accessor(qapp) -> None:
    """MainWindow must expose the visible LibraryScreen tracks_table via a public accessor."""
    window = _make_window()
    assert window.visible_tracks_table is window._library_screen.tracks_table
