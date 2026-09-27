"""Tests for LibraryScreen rendering."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QWidget

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.spectral_profile import (
    CURRENT_ANALYSIS_VERSION,
    SpectralProfile,
    format_spectral_color,
)
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_columns import column_index
from xfinaudio.desktop.library_controller import LibraryController
from xfinaudio.desktop.library_view_model import LibraryViewModel, TrackDisplayRow
from xfinaudio.desktop.screens.library_screen import _MISSING_COLUMN, LibraryScreen
from xfinaudio.desktop.window_service_wiring import apply_main_song_filter
from xfinaudio.library.models import TrackRecord


def _loudness_profile(
    true_peak_dbtp: float | None,
    *,
    status: LoudnessStatus = LoudnessStatus.MEASURED,
) -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=-10.2,
        loudness_range_lra=3.5,
        true_peak_dbtp=true_peak_dbtp,
        status=status,
        engine_fingerprint="test-engine",
    )


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


def test_scan_progress_bar_shows_spectral_completion_progress(qapp: QApplication) -> None:
    screen = LibraryScreen()
    vm = LibraryViewModel()

    screen.render(
        vm,
        AppState(
            Path("/music"),
            is_completing_spectral=True,
            spectral_progress_count=2500,
            spectral_total_count=10000,
        ),
        lightweight=True,
    )

    assert screen.scan_progress_bar.isHidden() is False
    assert screen.scan_progress_bar.value() == 25
    assert screen.scan_progress_label.text() == "Analyzing colors 2,500/10,000"

    screen.render(vm, AppState(selected_folder=Path("/music")), lightweight=True)
    assert screen.scan_progress_bar.isHidden() is True
    assert screen.scan_progress_label.text() == ""


def test_rescan_button_hidden_by_default(qapp: QApplication) -> None:
    """The rescan affordance is not visible until a change is detected and rendered."""
    screen = LibraryScreen()

    assert screen.rescan_button.isHidden() is True


def test_rescan_button_visibility_follows_render(qapp: QApplication) -> None:
    """Rendering shows/hides the rescan affordance per the view-model predicate."""
    screen = LibraryScreen()
    vm = LibraryViewModel()

    screen.render(vm, AppState(selected_folder=Path("/music"), changes_detected_since_scan=True), lightweight=True)
    assert screen.rescan_button.isHidden() is False

    screen.render(vm, AppState(selected_folder=Path("/music")), lightweight=True)
    assert screen.rescan_button.isHidden() is True


def test_rescan_button_click_emits_rescan_requested(qapp: QApplication) -> None:
    """Clicking the rescan affordance emits rescan_requested, mirroring scan_button."""
    screen = LibraryScreen()
    emitted: list[bool] = []
    screen.rescan_requested.connect(lambda: emitted.append(True))

    screen.rescan_button.click()

    assert emitted == [True]


def test_scan_progress_bar_shows_loudness_completion_progress(qapp: QApplication) -> None:
    screen = LibraryScreen()
    screen.render(
        LibraryViewModel(),
        AppState(
            selected_folder=Path("/music"),
            is_completing_loudness=True,
            loudness_progress_count=25,
            loudness_total_count=100,
        ),
        lightweight=True,
    )

    assert screen.scan_progress_bar.value() == 25
    assert screen.scan_progress_label.text() == "Analyzing loudness 25/100"


@pytest.mark.parametrize(
    ("true_peak_dbtp", "badge"),
    [(0.0, "True peak clipping"), (-0.5, "True peak warning"), (-1.0, ""), (-1.1, "")],
)
def test_loudness_detail_true_peak_badge_uses_exact_thresholds(
    qapp: QApplication, true_peak_dbtp: float, badge: str
) -> None:
    screen = LibraryScreen()

    screen.set_loudness_details(_loudness_profile(true_peak_dbtp), visible=True)

    assert screen.loudness_detail_label.text() == f"LUFS: -10.2 · LRA: 3.5 · True peak: {true_peak_dbtp:.1f} dBTP"
    assert screen.true_peak_badge.text() == badge
    assert screen.true_peak_badge.isHidden() is (badge == "")


def test_loudness_detail_honestly_handles_missing_and_too_short_profiles(qapp: QApplication) -> None:
    screen = LibraryScreen()

    screen.set_loudness_details(None, visible=True)
    assert screen.loudness_detail_label.text() == "Loudness: not measured"

    screen.set_loudness_details(_loudness_profile(None, status=LoudnessStatus.TRANSIENT_FAILURE), visible=True)
    assert screen.loudness_detail_label.text() == "Loudness: temporarily unavailable"

    screen.set_loudness_details(_loudness_profile(None, status=LoudnessStatus.TOO_SHORT), visible=True)
    assert screen.loudness_detail_label.text() == "LUFS: -10.2 · LRA: unavailable · True peak: unavailable (too short)"
    assert screen.true_peak_badge.isHidden() is True


def test_loudness_adds_exactly_one_library_table_column(qapp: QApplication) -> None:
    """The detail pane stayed the deep surface; the table gained only a per-row LUFS value.

    Supersedes the earlier contract that loudness must add no column at all: without a
    per-row indicator an hours-long analysis is invisible unless a row is selected.
    """
    screen = LibraryScreen()

    assert screen.tracks_table.columnCount() == 13


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


def test_empty_state_stays_hidden_for_a_restored_library_without_a_folder(qapp: QApplication) -> None:
    """A library restored from the database has records but no selected folder.

    The empty state only looked at `selected_folder`, so reopening the app
    announced "No library yet" above thousands of listed tracks.
    """
    screen = LibraryScreen()
    restored = _state_with_tracks().model_copy(update={"selected_folder": None})

    screen.render(LibraryViewModel(), restored, lightweight=True)

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


def _main_song_filter_harness(screen: LibraryScreen, state: AppState) -> SimpleNamespace:
    """Minimal stand-in exposing only the attributes apply_main_song_filter consumes."""
    return SimpleNamespace(
        _library_screen=screen,
        _records_by_path={record.path: record for record in state.scanned_records},
        _active_song_search_query="",
        _selected_metadata_status_filter=lambda: None,
        _selected_missing_metadata_filter=lambda: None,
        _refresh_idle_action_state=lambda: None,
    )


def test_main_song_filter_matches_artist_not_only_title(qapp: QApplication) -> None:
    """The main-window song filter must match Artist, not only Title.

    The wiring filter read the Title cell alone, so a DJ searching an artist
    name hid every row unless the name also appeared inside the title text.
    """
    screen = LibraryScreen()
    state = _state_with_duplicates()
    screen.render(LibraryViewModel(), state)
    harness = _main_song_filter_harness(screen, state)

    # Artist query keeps rows whose titles never mention the artist.
    apply_main_song_filter(harness, "dj richie rich")
    assert _visible_titles(screen) == ["Right On Track", "Right On Track (v2)"]

    # Title queries keep working.
    apply_main_song_filter(harness, "right on")
    assert _visible_titles(screen) == ["Right On Track", "Right On Track (v2)"]

    # A query matching neither title nor artist hides every row.
    apply_main_song_filter(harness, "no such match anywhere")
    assert _visible_titles(screen) == []

    # An empty query shows everything again.
    apply_main_song_filter(harness, "")
    assert _visible_titles(screen) == ["Right On Track", "Right On Track (v2)", "Other Song"]


# ---------------------------------------------------------------------------
# Render contract: same-rows skip, selection/scroll restore, in-place play state
# ---------------------------------------------------------------------------


def _state_with_named_tracks(*paths: str) -> AppState:
    return AppState(
        selected_folder=Path("/music"),
        scanned_records=[TrackRecord(path=path, title=Path(path).stem, metadata_status="complete") for path in paths],
    )


def _state_with_many_tracks(count: int) -> AppState:
    return AppState(
        selected_folder=Path("/music"),
        scanned_records=[
            TrackRecord(path=f"/music/track-{i}.flac", title=f"Track {i}", metadata_status="complete")
            for i in range(count)
        ],
    )


def _select_whole_rows(table, rows: list[int]) -> None:
    table.setCurrentCell(rows[0], 0)
    for row in rows:
        for col in range(table.columnCount()):
            table.item(row, col).setSelected(True)


def test_same_rows_render_preserves_multi_selection_current_row_and_scroll(qapp: QApplication) -> None:
    """Re-rendering identical rows must not collapse a multi-row selection.

    The old restore path called selectRow once per matched row, and each call
    replaces the previous selection in Qt, so selecting rows 0 and 1 collapsed
    to row 1 and dragged the current row along with it. The scroll assertion is
    a regression guard for explicit scroll restore after a rebuild.
    """
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = _state_with_many_tracks(40)
    screen.render(vm, state)

    table = screen.tracks_table
    _select_whole_rows(table, [0, 1])
    screen.resize(400, 300)
    screen.show()
    qapp.processEvents()
    scroll_bar = table.verticalScrollBar()
    assert scroll_bar.maximum() > 0
    scroll_bar.setValue(5)
    qapp.processEvents()

    screen.render(vm, state)

    assert sorted({idx.row() for idx in table.selectedIndexes()}) == [0, 1]
    assert table.currentRow() == 0
    assert scroll_bar.value() == 5


def test_rows_changed_render_updates_table_and_restores_all_persisting_selections(qapp: QApplication) -> None:
    """A rebuild with changed rows rewrites the content and re-selects every persisting path.

    Two persisting paths are selected on purpose: the old per-row selectRow
    restore collapsed them to the last match even when both still exist.
    """
    screen = LibraryScreen()
    vm = LibraryViewModel()
    screen.render(vm, _state_with_named_tracks("/music/a.flac", "/music/b.flac", "/music/c.flac"))

    table = screen.tracks_table
    _select_whole_rows(table, [0, 1])

    screen.render(vm, _state_with_named_tracks("/music/b.flac", "/music/a.flac", "/music/d.flac"))

    assert table.rowCount() == 3
    assert table.item(0, 0).text() == "b"
    path_col = table.columnCount() - 1
    selected_paths = {table.item(idx.row(), path_col).text() for idx in table.selectedIndexes()}
    assert selected_paths == {"/music/a.flac", "/music/b.flac"}


def test_set_playing_row_with_unchanged_records_does_not_rebuild(qapp: QApplication) -> None:
    """Play/pause toggles must not rebuild the table when the records are unchanged.

    The play-state highlight only touches the Preview cell and the row colors,
    so a full rebuild — which resets selection and currentRow — is pure waste;
    the update is applied in place instead.
    """
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = _state_with_tracks()
    screen.render(vm, state)

    populate_calls: list[int] = []
    original_populate = screen._populate_table

    def spying_populate(rows: list[TrackDisplayRow]) -> None:
        populate_calls.append(len(rows))
        original_populate(rows)

    screen._populate_table = spying_populate
    preview_col = column_index("Preview")

    screen.set_playing_row("/music/ready.flac")
    assert populate_calls == []
    assert screen.tracks_table.rowCount() == 3
    assert screen.tracks_table.item(0, preview_col).text() == "⏸"

    screen.set_playing_row(None)
    assert populate_calls == []
    assert screen.tracks_table.item(0, preview_col).text() == "▶"

    # A rebuild still happens when the records themselves change.
    screen.render(vm, _state_with_many_tracks(2))
    assert populate_calls == [2]


# ---------------------------------------------------------------------------
# Render cache invalidation: direct table writes bypassing _populate_table
# ---------------------------------------------------------------------------


def _controller_for(screen: LibraryScreen, state: AppState) -> LibraryController:
    """Build a minimal LibraryController wired to *screen* for direct-write tests."""
    widgets = SimpleNamespace(library_screen=screen, build_screen=None, status_label=QLabel(""))
    access = SimpleNamespace(
        settings_getter=lambda: None,
        settings_setter=lambda _settings: None,
        settings_repository=None,
        selected_paths=[],
        pre_scan_records_by_path={},
        set_applied_copilot_variant=lambda _variant: None,
        set_recommendation_sections_expanded=lambda _expanded: None,
        clear_recommendation_review=lambda: None,
        selected_track_controls=lambda: None,
        apply_song_filter=lambda *args, **kwargs: None,
        state_setter=lambda _state: None,
        export_metadata_status_to_serato=lambda *args, **kwargs: None,
        undo_manager=None,
        refresh_undo_state=lambda: None,
        workflow_tab_setter=lambda _index: None,
        open_track=lambda _path: None,
        live_load_next=lambda _path: None,
    )
    return LibraryController(
        state=state,
        workflow_service=cast(Any, None),
        widgets=cast(Any, widgets),
        access=cast(Any, access),
        audio_player=cast(Any, None),
        sync_state=lambda: None,
        tr=lambda text: text,
        log=logging.getLogger("test"),
        parent=QWidget(),
    )


def test_full_render_after_controller_populate_reconciles_active_sort(qapp: QApplication) -> None:
    """Rows written directly by the controller must reconcile on the next full render.

    LibraryController.populate_track_table writes the tracks table in scan
    order, bypassing _populate_table. With an active sort indicator the next
    render computed the same sorted signature and skipped the rebuild, leaving
    rows in scan order under a sorted header (verifier repro S4).
    """
    screen = LibraryScreen()
    vm = LibraryViewModel()
    records = [
        TrackRecord(path="/music/c.flac", title="Charlie", metadata_status="complete"),
        TrackRecord(path="/music/a.flac", title="Alpha", metadata_status="complete"),
        TrackRecord(path="/music/b.flac", title="Bravo", metadata_status="complete"),
    ]
    state = AppState(selected_folder=Path("/music"), scanned_records=records)
    screen.render(vm, state)

    title_col = column_index("Title")
    screen._on_header_double_clicked(title_col)  # activates the sort and re-renders
    assert [screen.tracks_table.item(row, title_col).text() for row in range(3)] == [
        "Alpha",
        "Bravo",
        "Charlie",
    ]

    controller = _controller_for(screen, state)
    controller.populate_track_table(records)  # direct write in scan order

    assert screen._last_rows_signature is None
    assert screen._last_render_extras is None

    screen.render(vm, controller._state)

    assert [screen.tracks_table.item(row, title_col).text() for row in range(3)] == [
        "Alpha",
        "Bravo",
        "Charlie",
    ]


def test_full_render_after_controller_populate_restores_playing_preview(qapp: QApplication) -> None:
    """A direct controller write while a track plays must not strand the Preview cell.

    populate_track_table rewrites every Preview cell to the play icon and the
    same-rows render skipped the rebuild because the extras (including the
    playing path) were unchanged, so the playing row never regained its paused
    icon (verifier repro S5).
    """
    screen = LibraryScreen()
    vm = LibraryViewModel()
    records = [
        TrackRecord(path="/music/ready.flac", title="Ready", metadata_status="complete"),
        TrackRecord(path="/music/other.flac", title="Other", metadata_status="complete"),
    ]
    state = AppState(selected_folder=Path("/music"), scanned_records=records)
    screen.render(vm, state)

    preview_col = column_index("Preview")
    screen.set_playing_row("/music/ready.flac")
    ready_row = screen._find_row_by_path("/music/ready.flac")
    assert ready_row is not None
    assert screen.tracks_table.item(ready_row, preview_col).text() == "⏸"

    controller = _controller_for(screen, state)
    controller.populate_track_table(records)  # direct write resets Preview cells

    assert screen._last_rows_signature is None
    assert screen._last_render_extras is None

    screen.render(vm, controller._state)

    playing_row = screen._find_row_by_path("/music/ready.flac")
    assert playing_row is not None
    assert screen.tracks_table.item(playing_row, preview_col).text() == "⏸"


# ---------------------------------------------------------------------------
# Analysis callbacks update state and paint the affected cell immediately.
# ---------------------------------------------------------------------------


def test_spectral_profile_ready_paints_color_cell_immediately(qapp: QApplication) -> None:
    """on_spectral_profile_ready must paint the Color cell in place, synchronously.

    Library sync renders are lightweight by design (app_controller hardcodes
    lightweight=True for the library tab), and ``render(lightweight=True)``
    returns before painting rows. The in-place cell write is therefore the
    production painter for the spectral pass's only visible output; deferring
    it to "the coalesced sync render" (the T3 premise) leaves the cell empty
    forever. The state update still runs first, so the row signature (which
    includes spectral_color) diverges and the next full render rebuilds the
    row from state — no drift is possible.
    """
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music")).with_scanned_records(
        [TrackRecord(path="/music/red.flac", title="Red", metadata_status="complete")]
    )
    screen.render(vm, state)
    color_col = column_index("Color")
    assert screen.tracks_table.item(0, color_col).text() == ""

    controller = _controller_for(screen, state)
    sync_requests: list[bool] = []
    controller._request_sync = lambda: sync_requests.append(True)

    profile = SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )
    controller.on_spectral_profile_ready("/music/red.flac", profile)

    # Immediate in-place paint: the cell shows the color synchronously,
    # without any render call (library sync renders are lightweight and
    # never paint rows).
    assert screen.tracks_table.item(0, color_col).text() == format_spectral_color(profile)
    assert sync_requests == [True]

    # The state update keeps signature parity: a full render rebuilds the row
    # from state with the same color, so the write-behind cannot drift.
    screen.render(vm, controller._state)
    assert screen.tracks_table.item(0, color_col).text() == format_spectral_color(profile)


# ---------------------------------------------------------------------------
# No silent-return slots: empty-selection guidance reaches the status label.
# ---------------------------------------------------------------------------


def test_open_selected_library_track_without_selection_reports_status(qapp: QApplication) -> None:
    """Opening a track with no library selection must surface guidance."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music")).with_scanned_records(
        [TrackRecord(path="/music/a.flac", title="A", metadata_status="complete")]
    )
    screen.render(vm, state)
    controller = _controller_for(screen, state)

    controller.open_selected_library_track()

    assert controller._widgets.status_label.text() != ""


def test_proceed_to_export_without_exportable_state_reports_status(qapp: QApplication) -> None:
    """Proceeding to export with no exportable playlist must surface guidance."""
    screen = LibraryScreen()
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music")).with_scanned_records(
        [TrackRecord(path="/music/a.flac", title="A", metadata_status="complete")]
    )
    screen.render(vm, state)
    controller = _controller_for(screen, state)

    controller.on_proceed_to_export()

    assert controller._widgets.status_label.text() != ""
