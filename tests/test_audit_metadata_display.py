"""Regression coverage for precise tempo and actionable metadata worklists."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from tests.test_build_screen import _recommendation
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.metadata_view_model import MetadataViewModel
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.screens.metadata_screen import MetadataScreen
from xfinaudio.library.models import TrackRecord


@pytest.mark.parametrize("bpm, expected", [(120.5, "120.5"), (120.125, "120.125"), (120.0, "120"), (None, "—")])
def test_tempo_display_agrees_across_library_review_and_metadata(bpm: float | None, expected: str) -> None:
    track = TrackRecord(path="/synthetic.flac", bpm=bpm)
    state = AppState(scanned_records=[track], last_recommendation=_recommendation([track]))
    assert LibraryViewModel().tracks_for_display(state)[0].bpm == expected
    assert ReviewViewModel().recommendation_rows(state)[0].bpm == expected
    assert MetadataViewModel().worklist_rows(state)[0].bpm == expected


def test_metadata_opens_on_incomplete_and_preserves_explicit_all(qapp: QApplication) -> None:
    state = AppState(
        scanned_records=[
            TrackRecord(path="/complete.flac", metadata_status="complete"),
            TrackRecord(path="/missing.flac", missing_required_fields=["bpm", "camelot_key", "energy_level"]),
        ]
    )
    screen = MetadataScreen()
    screen.render(state)
    assert screen.status_combo.currentText() == "Incomplete"
    assert screen.worklist_table.rowCount() == 1
    assert screen.worklist_table.item(0, 5).text() == "BPM, Key, Energy"
    assert screen.gap_export_button.text() == "Export repair checklist"
    screen.status_combo.setCurrentText("All")
    screen.render(state)
    assert screen.worklist_table.rowCount() == 2


def test_metadata_serato_export_runs_once_with_active_filters(qapp: QApplication) -> None:
    screen = MetadataScreen()
    window = Mock()
    screen.connect_signals(window)
    screen.render(AppState(scanned_records=[TrackRecord(path="/missing.flac")]))
    screen.status_combo.setCurrentText("Incomplete")
    screen.export_button.click()
    window._library_controller.on_metadata_export_requested.assert_called_once_with("Incomplete", "All")
    window.export_metadata_status_to_serato.assert_not_called()


def test_metadata_default_does_not_hide_complete_library_tracks(qapp: QApplication, tmp_path) -> None:
    window = MainWindow.with_defaults(tmp_path / "db.sqlite3", tmp_path / "settings.json")
    try:
        window.show_tracks([TrackRecord(path="/complete.flac", title="Complete", metadata_status="complete")])
        window._metadata_screen.render(window._state)
        window._apply_song_filter()
        assert window._metadata_screen.status_combo.currentText() == "Incomplete"
        assert not window._library_screen.tracks_table.isRowHidden(0)
    finally:
        window.close()


def test_metadata_refresh_routes_to_read_only_scan_only_when_idle(qapp: QApplication) -> None:
    screen = MetadataScreen()
    window = Mock()
    screen.connect_signals(window)
    state = AppState(selected_folder=Path("/synthetic"))
    screen.render(state)
    screen.refresh_button.click()
    window.scan_selected_folder.assert_called_once_with()
    screen.render(state.model_copy(update={"is_scanning": True}))
    assert not screen.refresh_button.isEnabled()
    screen.render(AppState())
    assert not screen.refresh_button.isEnabled()
