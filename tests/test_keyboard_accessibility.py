"""Keyboard accessibility tests for the XfinAudio desktop UI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanProgress


class FakeScanService:
    def __init__(self) -> None:
        self.scanned_folder: Path | None = None

    def scan(self, folder: Path, **kwargs):
        self.scanned_folder = folder
        progress_callback = kwargs.get("on_progress")
        if progress_callback is not None:
            progress_callback(ScanProgress(processed_count=1, total_count=1, current_path=folder / "track.flac"))
        return [
            TrackRecord(
                path=str(folder / "track.flac"),
                title="Track One",
                artist="Artist One",
                bpm=116.0,
                camelot_key="11B",
                energy_level=5,
                metadata_status="complete",
            ),
        ]


class FakeRepository:
    def __init__(self) -> None:
        self.saved_records: list[TrackRecord] = []

    def save_scan_results(self, records: list[TrackRecord]) -> None:
        self.saved_records = records


def ensure_app() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


def _make_window() -> MainWindow:
    return MainWindow(scan_service=FakeScanService(), repository=FakeRepository())


def test_library_screen_widgets_have_accessible_names() -> None:
    ensure_app()
    window = _make_window()
    screen = window._library_screen
    assert screen.folder_button.accessibleName()
    assert screen.scan_button.accessibleName()
    assert screen.cancel_button.accessibleName()
    assert screen.search_input.accessibleName()
    assert screen.tracks_table.accessibleName()
    assert screen.settings_button.accessibleName()
    assert screen.proceed_button.accessibleName()


def test_build_screen_widgets_have_accessible_names() -> None:
    ensure_app()
    window = _make_window()
    screen = window._build_screen
    assert screen.strategy_combo.accessibleName()
    assert screen.recommend_button.accessibleName()
    assert screen.exclude_button.accessibleName()
    assert screen.lock_button.accessibleName()
    assert screen.clear_constraints_button.accessibleName()
    assert screen.target_count_input.accessibleName()
    assert screen.genre_focus_input.accessibleName()
    assert screen.copilot_button.accessibleName()
    assert screen.copilot_table.accessibleName()
    assert screen.apply_variant_button.accessibleName()
    assert screen.back_button.accessibleName()
    assert screen.proceed_button.accessibleName()


def test_review_screen_widgets_have_accessible_names() -> None:
    ensure_app()
    window = _make_window()
    screen = window._review_screen
    assert screen.readiness_badge.accessibleName()
    assert screen.dj_readiness_label.accessibleName()
    assert screen.recommendation_table.accessibleName()
    assert screen.remove_track_button.accessibleName()
    assert screen.transition_table.accessibleName()
    assert screen.readiness_table.accessibleName()
    assert screen.back_button.accessibleName()
    assert screen.export_button.accessibleName()


def test_export_screen_widgets_have_accessible_names() -> None:
    ensure_app()
    window = _make_window()
    screen = window._export_screen
    assert screen.variant_label.accessibleName()
    assert screen.software_selector.accessibleName()
    assert screen.safe_folder_label.accessibleName()
    assert screen.safe_folder_button.accessibleName()
    assert screen.export_guidance_label.accessibleName()
    assert screen.preview_button.accessibleName()
    assert screen.export_button.accessibleName()
    assert screen.export_readiness_button.accessibleName()
    assert screen.history_table.accessibleName()
    assert screen.back_button.accessibleName()


def test_metadata_screen_widgets_have_accessible_names() -> None:
    ensure_app()
    window = _make_window()
    screen = window._metadata_screen
    assert screen.status_label.accessibleName()
    assert screen.guidance_label.accessibleName()
    assert screen.status_combo.accessibleName()
    assert screen.missing_combo.accessibleName()
    assert screen.export_button.accessibleName()
    assert screen.worklist_table.accessibleName()
    assert screen.back_button.accessibleName()


def test_keyboard_shortcuts_are_registered() -> None:
    ensure_app()
    window = _make_window()
    assert "open_folder" in window._keyboard_shortcuts
    assert "scan_metadata" in window._keyboard_shortcuts
    assert "recommend_playlist" in window._keyboard_shortcuts
    assert "export_recommendation" in window._keyboard_shortcuts
    assert "cancel_scan" in window._keyboard_shortcuts


def test_shortcut_open_folder_chooses_folder(tmp_path, monkeypatch) -> None:
    ensure_app()
    window = _make_window()

    def _choose(*_args, **_kwargs):
        return str(tmp_path)

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", _choose)

    window._keyboard_shortcuts["open_folder"].activated.emit()

    assert window.selected_folder == tmp_path


def test_shortcut_scan_metadata_invokes_scan_coordinator() -> None:
    ensure_app()
    window = _make_window()

    spy = MagicMock()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(window._scan_coordinator, "scan_selected_folder", spy)

    window._keyboard_shortcuts["scan_metadata"].activated.emit()

    spy.assert_called_once()
    monkeypatch.undo()


def test_shortcut_recommend_invokes_recommend_button() -> None:
    ensure_app()
    window = _make_window()

    # Enable the Build tab page so its buttons can be clicked.
    window.workflow_tabs.setTabEnabled(1, True)

    spy = MagicMock()
    window._build_screen.recommend_button.clicked.connect(spy)
    window._build_screen.recommend_button.setEnabled(True)

    window._keyboard_shortcuts["recommend_playlist"].activated.emit()

    spy.assert_called_once()


def test_shortcut_export_invokes_export_button() -> None:
    ensure_app()
    window = _make_window()

    # Enable the Export tab page so its buttons can be clicked.
    window.workflow_tabs.setTabEnabled(3, True)

    spy = MagicMock()
    window._export_screen.export_button.clicked.connect(spy)
    window._export_screen.export_button.setEnabled(True)

    window._keyboard_shortcuts["export_recommendation"].activated.emit()

    spy.assert_called_once()


def test_shortcut_escape_invokes_cancel_scan() -> None:
    ensure_app()
    window = _make_window()

    spy = MagicMock()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(window, "cancel_scan", spy)

    window._keyboard_shortcuts["cancel_scan"].activated.emit()

    spy.assert_called_once()
    monkeypatch.undo()


def test_primary_controls_accept_tab_focus() -> None:
    """Primary interactive controls have a tab-focus policy."""
    ensure_app()
    window = _make_window()

    library_controls = [
        window._library_screen.folder_button,
        window._library_screen.scan_button,
        window._library_screen.search_input,
        window._library_screen.tracks_table,
        window._library_screen.settings_button,
        window._library_screen.proceed_button,
    ]
    build_controls = [
        window._build_screen.strategy_combo,
        window._build_screen.recommend_button,
        window._build_screen.exclude_button,
        window._build_screen.lock_button,
        window._build_screen.clear_constraints_button,
        window._build_screen.target_count_input,
        window._build_screen.genre_focus_input,
        window._build_screen.copilot_button,
        window._build_screen.copilot_table,
        window._build_screen.apply_variant_button,
        window._build_screen.back_button,
        window._build_screen.proceed_button,
    ]
    review_controls = [
        window._review_screen.recommendation_table,
        window._review_screen.remove_track_button,
        window._review_screen.transition_table,
        window._review_screen.readiness_table,
        window._review_screen.back_button,
        window._review_screen.export_button,
    ]
    export_controls = [
        window._export_screen.software_selector,
        window._export_screen.safe_folder_button,
        window._export_screen.preview_button,
        window._export_screen.export_button,
        window._export_screen.export_readiness_button,
        window._export_screen.history_table,
        window._export_screen.back_button,
    ]
    metadata_controls = [
        window._metadata_screen.status_combo,
        window._metadata_screen.missing_combo,
        window._metadata_screen.export_button,
        window._metadata_screen.worklist_table,
        window._metadata_screen.back_button,
    ]

    for widget in library_controls + build_controls + review_controls + export_controls + metadata_controls:
        assert widget.focusPolicy() != Qt.FocusPolicy.NoFocus, f"{widget.objectName()} should accept tab focus"
