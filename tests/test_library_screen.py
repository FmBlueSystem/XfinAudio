"""Tests for LibraryScreen rendering."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QFrame

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.screens.library_screen import _MISSING_COLUMN, LibraryScreen
from xfinaudio.library.models import TrackRecord


def _state_with_tracks() -> AppState:
    return AppState(
        selected_folder=Path("/music"),
        scanned_records=[
            TrackRecord(path="/music/ready.flac", title="Ready", metadata_status="complete"),
            TrackRecord(path="/music/no-bpm.flac", title="No BPM", missing_required_fields=["bpm"]),
            TrackRecord(path="/music/no-key.flac", title="No Key", missing_required_fields=["camelot_key"]),
        ],
    )


def test_library_screen_renders_scan_settings_review(qapp: QApplication) -> None:
    """The scan settings review label is updated when the screen renders."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music"))

    screen.render(vm, state, lightweight=True)

    expected = vm.scan_settings_review_text(state)
    assert screen.scan_settings_label.text() == expected
    assert ".mp3" in screen.scan_settings_label.text()
    assert "TBPM" in screen.scan_settings_label.text()


def test_missing_column_is_hidden_by_default(qapp: QApplication) -> None:
    """The Missing column starts hidden to preserve horizontal table space."""
    screen = LibraryScreen()

    assert screen.tracks_table.isColumnHidden(_MISSING_COLUMN) is True
    assert screen.missing_column_button.text() == "Show Missing"


def test_toggle_button_shows_and_hides_missing_column(qapp: QApplication) -> None:
    """The toggle button reveals and hides the Missing column."""
    screen = LibraryScreen()

    screen.missing_column_button.click()

    assert screen.tracks_table.isColumnHidden(_MISSING_COLUMN) is False
    assert screen.missing_column_button.text() == "Hide Missing"

    screen.missing_column_button.click()

    assert screen.tracks_table.isColumnHidden(_MISSING_COLUMN) is True
    assert screen.missing_column_button.text() == "Show Missing"


def test_quick_filter_buttons_filter_rows_and_clear(qapp: QApplication) -> None:
    """Quick filter buttons update the table and clear back to the full library."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = _state_with_tracks()

    assert screen.quick_filter_layout is not None
    assert all(button.isCheckable() for button in screen.quick_filter_buttons)
    screen.render(vm, state)
    screen.missing_bpm_filter_button.click()

    assert screen.missing_bpm_filter_button.isChecked() is True
    assert screen.active_filter_count_label.text() == "1 active"
    assert screen.tracks_table.rowCount() == 1
    assert screen.tracks_table.item(0, 0).text() == "No BPM"

    screen.clear_filters_button.click()

    assert screen.missing_bpm_filter_button.isChecked() is False
    assert screen.active_filter_count_label.text() == "0 active"
    assert screen.tracks_table.rowCount() == 3


def test_scan_progress_bar_shows_eta_and_hides_when_complete(qapp: QApplication) -> None:
    screen = LibraryScreen()
    vm = LibraryViewModel()

    screen.render(
        vm,
        AppState(
            Path("/music"), is_scanning=True, scan_progress_count=1, scan_progress_total=4, scan_elapsed_seconds=30
        ),
        lightweight=True,
    )

    assert screen.scan_progress_bar.isHidden() is False
    assert screen.scan_progress_bar.value() == 25
    assert screen.scan_progress_label.text() == "25% · 1:30 remaining"
    screen.render(vm, AppState(selected_folder=Path("/music")), lightweight=True)
    assert screen.scan_progress_bar.isHidden() is True
    assert screen.scan_progress_label.text() == ""


def test_primary_and_secondary_action_buttons_have_visual_hierarchy(qapp: QApplication) -> None:
    """Scan is a larger primary action; Settings is a smaller muted secondary action."""
    screen = LibraryScreen()

    assert screen.scan_button.objectName() == "primaryAction"
    assert screen.settings_button.objectName() == "secondaryAction"
    assert screen.scan_button.minimumHeight() > screen.settings_button.maximumHeight()


def test_section_divider_separates_controls_from_table(qapp: QApplication) -> None:
    """A horizontal QFrame divider sits between the controls and the table."""
    screen = LibraryScreen()

    assert screen.section_divider.frameShape() == QFrame.Shape.HLine


def test_empty_state_shows_no_library_then_no_tracks(qapp: QApplication) -> None:
    """Empty-state label guides the user when there is no library, then no tracks."""
    screen = LibraryScreen()
    vm = LibraryViewModel()

    screen.render(vm, AppState(), lightweight=True)
    assert screen.empty_state_label.isHidden() is False
    assert "folder" in screen.empty_state_label.text().casefold()

    screen.render(vm, AppState(selected_folder=Path("/music")), lightweight=True)
    assert screen.empty_state_label.isHidden() is False
    assert "scan" in screen.empty_state_label.text().casefold()

    screen.render(vm, _state_with_tracks())
    assert screen.empty_state_label.isHidden() is True
