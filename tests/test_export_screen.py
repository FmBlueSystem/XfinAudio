from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.screens.export_screen import _HISTORY_COLUMNS, ExportScreen


def test_export_progress_bar_shows_eta_and_hides_when_complete(qapp: QApplication) -> None:
    screen = ExportScreen()
    vm = ExportViewModel()

    screen.render(
        vm,
        AppState(is_exporting=True, export_progress_count=3, export_progress_total=6, export_elapsed_seconds=90),
        lightweight=True,
    )

    assert screen.export_progress_bar.isHidden() is False
    assert screen.export_progress_bar.value() == 50
    assert screen.export_progress_label.text() == "50% · 1:30 remaining"
    screen.render(vm, AppState(), lightweight=True)
    assert screen.export_progress_bar.isHidden() is True
    assert screen.export_progress_label.text() == ""


def test_primary_and_secondary_action_buttons_have_visual_hierarchy(qapp: QApplication) -> None:
    """Export is a larger accent primary action; Back and Preview are smaller muted secondaries.

    The Export button keeps its established ``seratoExportButton`` accent objectName
    (gold primary accent) rather than the generic ``primaryAction`` cyan accent.
    """
    screen = ExportScreen()

    assert screen.export_button.objectName() == "seratoExportButton"
    assert screen.back_button.objectName() == "secondaryAction"
    assert screen.preview_button.objectName() == "secondaryAction"
    assert screen.export_button.minimumHeight() > screen.back_button.maximumHeight()


def test_section_divider_separates_controls_from_table(qapp: QApplication) -> None:
    """A horizontal QFrame divider sits between the controls and the history table."""
    screen = ExportScreen()

    assert screen.section_divider.frameShape() == QFrame.Shape.HLine


def test_all_buttons_have_tooltips(qapp: QApplication) -> None:
    """Every QPushButton on the screen exposes a non-empty tooltip (R1)."""
    from PySide6.QtWidgets import QPushButton

    screen = ExportScreen()

    buttons = screen.findChildren(QPushButton)
    assert buttons
    assert all(button.toolTip().strip() for button in buttons)


def test_history_table_headers_have_tooltips(qapp: QApplication) -> None:
    """Every export-history column header carries an explanatory tooltip (R2)."""
    screen = ExportScreen()

    table = screen.history_table
    tooltips = [table.horizontalHeaderItem(col).toolTip() for col in range(table.columnCount())]
    assert all(tip.strip() for tip in tooltips)


def test_history_paths_get_more_width_than_the_count_column(qapp: QApplication) -> None:
    """Three columns hold file paths; Tracks holds a number. All six were 107px."""
    screen = ExportScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    header = screen.history_table.horizontalHeader()
    width = {name: header.sectionSize(index) for index, name in enumerate(_HISTORY_COLUMNS)}

    for path_column in ("Serato Crate", "Readiness JSON", "Readiness CSV"):
        assert width[path_column] > width["Tracks"], f"{path_column} is no wider than the count column"


# ---------------------------------------------------------------------------
# Track list — the DJ sees what is about to be written and can edit it.
#
# The screen previously showed only a "15 tracks -> same_energy" summary, and
# the panel holding it stretched to fill the window because the history table
# is hidden until the first export. The set itself was never visible, and the
# only way to change it was to regenerate the whole thing.
# ---------------------------------------------------------------------------


def _recommendation_with(paths: list[str]):
    from xfinaudio.library.models import TrackRecord
    from xfinaudio.recommendation.playlist_service import recommend_playlist

    tracks = [
        TrackRecord(
            path=path,
            title=path.rsplit("/", maxsplit=1)[-1],
            artist="Artist",
            bpm=120.0 + index,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        )
        for index, path in enumerate(paths)
    ]
    return recommend_playlist(tracks, "same_energy")


def test_track_table_lists_the_tracks_that_will_be_exported(qapp: QApplication) -> None:
    screen = ExportScreen()
    recommendation = _recommendation_with(["/a.flac", "/b.flac", "/c.flac"])

    screen.render(ExportViewModel(), AppState(last_recommendation=recommendation), lightweight=True)

    assert screen.tracks_table.rowCount() == 3
    assert screen.visible_track_paths() == [item.path for item in recommendation.ordered_tracks]


def test_moving_a_track_down_emits_the_new_order(qapp: QApplication) -> None:
    screen = ExportScreen()
    recommendation = _recommendation_with(["/a.flac", "/b.flac", "/c.flac"])
    screen.render(ExportViewModel(), AppState(last_recommendation=recommendation), lightweight=True)
    original = screen.visible_track_paths()
    emitted: list[list[str]] = []
    screen.tracks_reordered.connect(emitted.append)

    screen.tracks_table.selectRow(0)
    screen.move_down_button.click()

    expected = [original[1], original[0], original[2]]
    assert emitted == [expected]
    assert screen.visible_track_paths() == expected


def test_moving_a_track_up_emits_the_new_order(qapp: QApplication) -> None:
    screen = ExportScreen()
    screen.render(
        ExportViewModel(), AppState(last_recommendation=_recommendation_with(["/a.flac", "/b.flac"])), lightweight=True
    )
    original = screen.visible_track_paths()
    emitted: list[list[str]] = []
    screen.tracks_reordered.connect(emitted.append)

    screen.tracks_table.selectRow(1)
    screen.move_up_button.click()

    assert emitted == [[original[1], original[0]]]


def test_moving_past_an_edge_does_nothing(qapp: QApplication) -> None:
    """No wraparound: the top track cannot become the last one by one click."""
    screen = ExportScreen()
    screen.render(
        ExportViewModel(), AppState(last_recommendation=_recommendation_with(["/a.flac", "/b.flac"])), lightweight=True
    )
    emitted: list[list[str]] = []
    screen.tracks_reordered.connect(emitted.append)

    screen.tracks_table.selectRow(0)
    screen.move_up_button.click()
    screen.tracks_table.selectRow(1)
    screen.move_down_button.click()

    assert emitted == []


def test_removing_a_track_emits_its_path(qapp: QApplication) -> None:
    screen = ExportScreen()
    screen.render(
        ExportViewModel(),
        AppState(last_recommendation=_recommendation_with(["/a.flac", "/b.flac", "/c.flac"])),
        lightweight=True,
    )
    doomed = screen.visible_track_paths()[1]
    emitted: list[str] = []
    screen.track_removed.connect(emitted.append)

    screen.tracks_table.selectRow(1)
    screen.remove_button.click()

    assert emitted == [doomed]


def test_edit_buttons_stay_disabled_without_a_selection(qapp: QApplication) -> None:
    screen = ExportScreen()
    screen.render(
        ExportViewModel(), AppState(last_recommendation=_recommendation_with(["/a.flac", "/b.flac"])), lightweight=True
    )
    screen.tracks_table.clearSelection()

    assert screen.move_up_button.isEnabled() is False
    assert screen.move_down_button.isEnabled() is False
    assert screen.remove_button.isEnabled() is False


def test_track_table_is_empty_without_a_recommendation(qapp: QApplication) -> None:
    screen = ExportScreen()

    screen.render(ExportViewModel(), AppState(), lightweight=True)

    assert screen.tracks_table.rowCount() == 0
    assert screen.visible_track_paths() == []


def test_editing_the_table_changes_what_the_crate_will_contain(qapp: QApplication) -> None:
    """The whole point: the crate is written from state, not from the table.

    Without the wiring the DJ reorders rows, hits Export, and gets the
    untouched original.
    """
    from xfinaudio.desktop.app_state_transitions import apply_export_track_order, apply_export_track_removal

    class _Window:
        _build_screen = None

        def __init__(self, state: AppState) -> None:
            self._state = state

        def _replace_app_state(self, state: AppState) -> None:
            self._state = state

    screen = ExportScreen()
    window = _Window(AppState(last_recommendation=_recommendation_with(["/a.flac", "/b.flac", "/c.flac"])))
    screen.tracks_reordered.connect(lambda paths: screen._apply_track_order(window, paths))
    screen.track_removed.connect(lambda path: screen._apply_track_removal(window, path))
    screen.render(ExportViewModel(), window._state, lightweight=True)
    original = screen.visible_track_paths()

    screen.tracks_table.selectRow(0)
    screen.move_down_button.click()

    assert window._state.last_recommendation is not None
    assert [t.path for t in window._state.last_recommendation.ordered_tracks] == [
        original[1],
        original[0],
        original[2],
    ]

    screen.tracks_table.selectRow(2)
    screen.remove_button.click()

    assert [t.path for t in window._state.last_recommendation.ordered_tracks] == [original[1], original[0]]
    assert apply_export_track_order and apply_export_track_removal  # imported for intent


def test_render_does_not_fight_the_user_after_their_own_edit(qapp: QApplication) -> None:
    """A re-render carrying the edited order back must not reset the selection."""
    screen = ExportScreen()
    recommendation = _recommendation_with(["/a.flac", "/b.flac", "/c.flac"])
    screen.render(ExportViewModel(), AppState(last_recommendation=recommendation), lightweight=True)
    screen.tracks_table.selectRow(1)

    screen.render(ExportViewModel(), AppState(last_recommendation=recommendation), lightweight=True)

    assert screen.tracks_table.selectionModel().selectedRows()[0].row() == 1
