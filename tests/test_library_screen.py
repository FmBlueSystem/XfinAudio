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


def _state_with_duplicates() -> AppState:
    return AppState(
        selected_folder=Path("/music"),
        scanned_records=[
            TrackRecord(
                path="/music/song-clean.flac",
                title="Right On Track",
                artist="DJ Richie Rich",
                metadata_status="complete",
            ),
            TrackRecord(
                path="/music/song-v2.flac",
                title="Right On Track (v2)",
                artist="DJ Richie Rich",
                missing_required_fields=["bpm"],
            ),
            TrackRecord(
                path="/music/other.flac",
                title="Other Song",
                artist="Someone",
                metadata_status="complete",
            ),
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


def test_bpm_sort_keeps_missing_values_last_in_both_directions(qapp: QApplication) -> None:
    screen = LibraryScreen()
    state = AppState(
        selected_folder=Path("/music"),
        scanned_records=[
            TrackRecord(path="/music/missing.flac", title="Missing", missing_required_fields=["bpm"]),
            TrackRecord(path="/music/slow.flac", title="Slow", bpm=100.0),
            TrackRecord(path="/music/fast.flac", title="Fast", bpm=130.0),
        ],
    )
    screen.render(LibraryViewModel(), state)

    screen._on_header_double_clicked(2)
    assert [screen.tracks_table.item(row, 0).text() for row in range(3)] == ["Slow", "Fast", "Missing"]

    screen._on_header_double_clicked(2)
    assert [screen.tracks_table.item(row, 0).text() for row in range(3)] == ["Fast", "Slow", "Missing"]


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


def test_all_buttons_have_tooltips(qapp: QApplication) -> None:
    """Every QPushButton on the screen exposes a non-empty tooltip (R1)."""
    from PySide6.QtWidgets import QPushButton

    screen = LibraryScreen()

    buttons = screen.findChildren(QPushButton)
    assert buttons
    assert all(button.toolTip().strip() for button in buttons)


def test_help_button_opens_help_dialog(qapp: QApplication) -> None:
    """The 'What's this?' help button builds a dialog with explanatory text (R3)."""
    screen = LibraryScreen()

    assert "what" in screen.help_button.text().casefold()
    dialog = screen.build_help_dialog()
    assert "scan" in dialog.text().casefold()


def test_tour_button_provides_walkthrough_steps(qapp: QApplication) -> None:
    """The 'Tour' button exposes an ordered, non-empty walkthrough (R4)."""
    screen = LibraryScreen()

    assert "tour" in screen.tour_button.text().casefold()
    steps = screen.tour_steps()
    assert len(steps) >= 3
    assert all(step.strip() for step in steps)


# ---------------------------------------------------------------------------
# Hide Duplicates quick filter — R4, R5, R6
# ---------------------------------------------------------------------------


def _visible_titles(screen: LibraryScreen) -> list[str]:
    return [
        screen.tracks_table.item(row, 0).text()
        for row in range(screen.tracks_table.rowCount())
        if not screen.tracks_table.isRowHidden(row)
    ]


def test_hide_duplicates_button_collapses_duplicate_rows(qapp: QApplication) -> None:
    """Toggling Hide Duplicates hides all but the representative row of a group (R4)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_duplicates())

    screen.hide_duplicates_button.click()

    visible = _visible_titles(screen)
    assert visible.count("Right On Track") == 1
    assert "Right On Track (v2)" not in visible
    assert "Other Song" in visible


def test_hide_duplicates_button_off_shows_all_rows(qapp: QApplication) -> None:
    """Hide Duplicates off leaves all rows visible — no-op for dedup (R4)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_duplicates())

    visible = _visible_titles(screen)
    assert "Right On Track" in visible
    assert "Right On Track (v2)" in visible
    assert "Other Song" in visible


def test_search_does_not_unhide_suppressed_duplicates(qapp: QApplication) -> None:
    """Typing into search after enabling Hide Duplicates never un-hides a suppressed row (R4)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_duplicates())
    screen.hide_duplicates_button.click()

    screen._on_search_changed("Track")  # matches both "Right On Track" variants

    visible = _visible_titles(screen)
    assert "Right On Track (v2)" not in visible
    assert "Right On Track" in visible


def test_duplicate_filter_only_considers_search_visible_rows(qapp: QApplication) -> None:
    """Dedup only looks at rows search already matched — a lone visible variant stays visible (R4)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_duplicates())
    screen.hide_duplicates_button.click()

    screen._on_search_changed("v2")  # only the v2 variant matches; it becomes a singleton among visible rows

    assert _visible_titles(screen) == ["Right On Track (v2)"]


def test_hide_duplicates_button_independent_of_status_mutual_exclusion(qapp: QApplication) -> None:
    """Hide Duplicates does not participate in the Complete/Incomplete mutual exclusion (R5)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_tracks())

    screen.complete_filter_button.click()
    screen.hide_duplicates_button.click()

    assert screen.complete_filter_button.isChecked() is True
    assert screen.hide_duplicates_button.isChecked() is True

    screen.incomplete_filter_button.click()

    assert screen.hide_duplicates_button.isChecked() is True
    assert screen.complete_filter_button.isChecked() is False


def test_hide_duplicates_toggle_does_not_uncheck_missing_filters(qapp: QApplication) -> None:
    """Hide Duplicates toggling has no effect on the Missing-* mutual exclusion group (R5)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_tracks())

    screen.missing_bpm_filter_button.click()
    screen.hide_duplicates_button.click()

    assert screen.missing_bpm_filter_button.isChecked() is True


def test_clear_filters_includes_hide_duplicates_button(qapp: QApplication) -> None:
    """Clear Filters resets Hide Duplicates alongside every other quick filter (R5)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_tracks())

    screen.hide_duplicates_button.click()
    screen.clear_filters_button.click()

    assert screen.hide_duplicates_button.isChecked() is False


def test_restore_quick_filters_restores_hide_duplicates_button(qapp: QApplication) -> None:
    """Undo-restore re-checks Hide Duplicates the same way as other quick filters (R5)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_tracks())

    labels = [screen.hide_duplicates_button.text()]
    screen.restore_quick_filters(labels)

    assert screen.hide_duplicates_button.isChecked() is True


def test_active_filter_count_includes_hide_duplicates_button(qapp: QApplication) -> None:
    """The active-filter count sum includes Hide Duplicates (R5)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_tracks())

    screen.hide_duplicates_button.click()
    assert screen.active_filter_count_label.text() == "1 active"

    screen.complete_filter_button.click()
    assert screen.active_filter_count_label.text() == "2 active"


def test_duplicate_count_label_empty_when_toggle_off(qapp: QApplication) -> None:
    """The duplicate-count label is empty while Hide Duplicates is off (R6)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_duplicates())

    assert screen.duplicate_count_label.text() == ""


def test_duplicate_count_label_shows_count_when_enabled(qapp: QApplication) -> None:
    """The duplicate-count label reflects the number of suppressed rows, singular (R6)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_duplicates())

    screen.hide_duplicates_button.click()

    assert screen.duplicate_count_label.text() == "1 duplicate hidden"


def test_duplicate_count_label_distinct_from_toggle_off_when_no_duplicates(qapp: QApplication) -> None:
    """Toggle-on-but-nothing-found reads differently from toggle-off, so the two states
    are distinguishable to the user (R6)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_tracks())

    screen.hide_duplicates_button.click()

    assert screen.duplicate_count_label.text() == "No duplicates found"
    assert screen.duplicate_count_label.text() != ""


def test_duplicate_count_label_clears_when_toggle_off_again(qapp: QApplication) -> None:
    """The duplicate-count label resets to empty once the toggle is switched off (R6)."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_duplicates())

    screen.hide_duplicates_button.click()
    assert screen.duplicate_count_label.text() != ""

    screen.hide_duplicates_button.click()
    assert screen.duplicate_count_label.text() == ""
