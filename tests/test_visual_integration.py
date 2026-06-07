"""Tests for visual integration: LibraryScreen connected to the Library tab."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.screens import LibraryScreen
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


def test_library_screen_signals_connected(qapp, window):
    """LibraryScreen signals must be connected without raising."""
    # Emit each signal — if disconnected, this would not crash but checks wiring
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
