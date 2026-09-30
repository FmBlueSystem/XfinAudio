from __future__ import annotations

from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.dj_readiness_controller import DjReadinessController
from xfinaudio.desktop.review_view_model import RecommendationRow, ReviewViewModel
from xfinaudio.desktop.screens.review_screen import _READINESS_COLUMNS, _TRANSITION_COLUMNS, ReviewScreen
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import ScoringWeights, TransitionScore
from xfinaudio.recommendation.strategies import PlaylistStrategy


def test_all_buttons_have_tooltips(qapp: QApplication) -> None:
    """Every QPushButton on the screen exposes a non-empty tooltip (R1)."""
    screen = ReviewScreen()

    buttons = screen.findChildren(QPushButton)
    assert buttons
    assert all(button.toolTip().strip() for button in buttons)


def test_recommendation_table_headers_have_tooltips(qapp: QApplication) -> None:
    """Every recommendation table column header carries an explanatory tooltip (R2)."""
    screen = ReviewScreen()

    table = screen.recommendation_table
    tooltips = [table.horizontalHeaderItem(col).toolTip() for col in range(table.columnCount())]
    assert all(tip.strip() for tip in tooltips)


def test_tables_use_the_free_vertical_space(qapp: QApplication) -> None:
    """The three tables should share the screen, not be squeezed above dead space.

    All three carry stretch factor 1, but a trailing addStretch(1) competed with
    them, so the free height was split four ways and a quarter went to nothing.
    Measured at 1200x660: 108px per table, about two visible rows each, with
    337px left over.
    """
    screen = ReviewScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    tables = (screen.recommendation_table, screen.transition_table, screen.readiness_table)
    visible_rows = [
        table.viewport().height() // max(table.verticalHeader().defaultSectionSize(), 1) for table in tables
    ]

    assert all(rows >= 4 for rows in visible_rows), f"only {visible_rows} rows visible per table"
    assert sum(table.height() for table in tables) > 0.65 * screen.height()


def test_summary_score_is_reported_once(qapp: QApplication) -> None:
    """Two labels showed the same numbers in different formats, stacked.

    review_summary_label already carries the transition count, warning count and
    average score, and ten call sites drive it. quality_label restated a subset
    of that one line below, and nothing outside this screen referenced it.
    """
    screen = ReviewScreen()

    assert hasattr(screen, "review_summary_label")
    assert not hasattr(screen, "quality_label"), "the duplicate summary label is back"


def test_transition_columns_give_space_to_track_names_not_scores(qapp: QApplication) -> None:
    """Every column stretched equally, so scores got as much room as track titles.

    Measured at 1200px: all nine columns landed on ~131px, enough for "Order" to
    show a single digit while "From"/"To" truncated the titles that make the row
    readable.
    """
    screen = ReviewScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    header = screen.transition_table.horizontalHeader()
    width = {name: header.sectionSize(index) for index, name in enumerate(_TRANSITION_COLUMNS)}

    for score_column in ("Order", "Key", "BPM", "Energy", "Tag", "Fit", "Blend", "Final"):
        assert width[score_column] < width["From"], f"{score_column} is as wide as the track name column"
        assert width[score_column] < width["To"], f"{score_column} is as wide as the track name column"


def test_transition_table_exposes_fit_and_blend_headers(qapp: QApplication) -> None:
    screen = ReviewScreen()
    table = screen.transition_table

    assert table.columnCount() == 11
    assert [table.horizontalHeaderItem(column).text() for column in range(11)] == [
        "Order",
        "From",
        "To",
        "Key",
        "BPM",
        "Energy",
        "Fit",
        "Blend",
        "Tag",
        "Final",
        "Warnings",
    ]
    assert table.horizontalHeaderItem(6).toolTip() == (
        "Do these tracks belong in the same set? Harmony, tags, danceability and spectral colour."
    )
    assert table.horizontalHeaderItem(7).toolTip() == (
        "Can these tracks be joined? Tempo and the energy handoff from the outgoing to the incoming section."
    )
    # Deliberately strategy-agnostic: the old text pinned harmonic_journey's
    # weights but was shown for every strategy.
    final_tooltip = table.horizontalHeaderItem(9).toolTip()
    assert final_tooltip.startswith("Weighted average")
    assert "depend on the selected strategy" in final_tooltip


def test_readiness_detail_column_gets_the_free_width(qapp: QApplication) -> None:
    """Check and Status hold short labels; Detail holds the sentence."""
    screen = ReviewScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    header = screen.readiness_table.horizontalHeader()
    check, status, detail = (header.sectionSize(index) for index in range(3))

    assert detail > check
    assert detail > status


def test_warning_column_keeps_usable_width_at_a_normal_window_size(qapp: QApplication) -> None:
    """Regression: eleven columns squeezed Warnings down to a sliver.

    Long score headers ("Energy Score", "Tag Score") forced content-sized
    columns far wider than the four characters they show, so the stretched
    Warnings column collapsed to ~16px and the alerts the summary counts
    were unreadable.
    """
    screen = ReviewScreen()
    screen.resize(1440, 900)
    screen.show()
    qapp.processEvents()

    header = screen.transition_table.horizontalHeader()
    widths = {_TRANSITION_COLUMNS[index]: header.sectionSize(index) for index in range(len(_TRANSITION_COLUMNS))}

    assert widths["Warnings"] >= 120, f"Warnings collapsed to {widths['Warnings']}px"
    for score_column in ("Key", "BPM", "Energy", "Fit", "Blend", "Tag", "Final"):
        assert widths[score_column] <= 90, f"{score_column} takes {widths[score_column]}px for a 5-character score"


def test_theme_column_widths_cover_every_table_column() -> None:
    """Regression: the width tuple silently fell behind the column list.

    `_REVIEW_TABLE_COLUMN_WIDTHS` held nine entries after the table grew to
    eleven columns, so every width landed on the wrong column and the last two
    got none — Warnings collapsed to 17px at 1440px wide. Nothing failed;
    the table just looked wrong.
    """
    from xfinaudio.desktop.theme import (
        _DJ_READINESS_TABLE_COLUMN_WIDTHS,
        _REVIEW_TABLE_COLUMN_WIDTHS,
    )

    assert len(_REVIEW_TABLE_COLUMN_WIDTHS) == len(_TRANSITION_COLUMNS)
    assert len(_DJ_READINESS_TABLE_COLUMN_WIDTHS) == len(_READINESS_COLUMNS)


# ----------------------------------------------------------------------
# Idempotent render + selection restore (render-contract-hardening T2)
# ----------------------------------------------------------------------


def _track(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        artist="Test Artist",
        bpm=128.0,
        camelot_key="8A",
        energy_level=7,
        metadata_status="complete",
    )


def _recommendation(tracks: list[TrackRecord]) -> PlaylistRecommendation:
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=PlaylistStrategy(
            name="harmonic_journey",
            display_name="Harmonic Journey",
            description="Test strategy",
            weights=ScoringWeights(),
        ),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def _state(paths: list[str]) -> AppState:
    tracks = [_track(path) for path in paths]
    return AppState(scanned_records=tracks, last_recommendation=_recommendation(tracks))


def _selected_paths(screen: ReviewScreen) -> list[str]:
    """Paths (UserRole on column 0) of every currently selected row."""
    table = screen.recommendation_table
    paths = []
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is not None and item.isSelected():
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                paths.append(path)
    return paths


def test_selection_survives_same_rows_render(qapp: QApplication) -> None:
    """A second render with unchanged rows must not wipe selection or currentRow.

    render() runs on every coalesced state sync while the Review tab is visible
    (~5 times per second during scans), so the destructive setRowCount(0)
    rebuild fired constantly and the DJ's selection — which drives the Remove
    button and double-click play — kept disappearing.
    """
    screen = ReviewScreen()
    vm = ReviewViewModel()
    state = _state(["/music/a.mp3", "/music/b.mp3"])

    screen.render(vm, state)
    screen.recommendation_table.selectRow(1)
    assert screen.recommendation_table.currentRow() == 1

    screen.render(vm, state)

    assert screen.recommendation_table.rowCount() == 2
    assert screen.recommendation_table.currentRow() == 1
    assert _selected_paths(screen) == ["/music/b.mp3"]


def test_selection_restored_by_path_when_rows_change(qapp: QApplication) -> None:
    """When rows change, every previously selected path that still exists is re-selected.

    The restore must follow the track path (UserRole on column 0), not the row
    position, so a reordered playlist keeps the same tracks selected. The
    currentRow follows the previously current track's path.
    """
    screen = ReviewScreen()
    vm = ReviewViewModel()
    screen.render(vm, _state(["/music/a.mp3", "/music/b.mp3", "/music/c.mp3"]))

    table = screen.recommendation_table
    # MultiSelection so two tracks can genuinely be selected at once; the
    # default single-selection mode would collapse this to one row in setup.
    from PySide6.QtWidgets import QAbstractItemView

    table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    table.setCurrentCell(1, 0)  # current track: /music/b.mp3
    for row in (0, 1):  # select /music/a.mp3 and /music/b.mp3
        for col in range(table.columnCount()):
            table.item(row, col).setSelected(True)

    screen.render(vm, _state(["/music/d.mp3", "/music/c.mp3", "/music/b.mp3", "/music/a.mp3"]))

    assert sorted(_selected_paths(screen)) == ["/music/a.mp3", "/music/b.mp3"]
    assert table.item(table.currentRow(), 0).data(Qt.ItemDataRole.UserRole) == "/music/b.mp3"


def test_remove_click_without_selection_reports_status(qapp: QApplication) -> None:
    """Remove with nothing selected must report guidance, not fail silently."""
    screen = ReviewScreen()
    window = Mock()
    screen.connect_signals(window)

    screen._on_remove_clicked()

    window.status_label.setText.assert_called_once_with("Select a track in the playlist before removing it")


def test_remove_click_without_valid_path_reports_status(qapp: QApplication) -> None:
    """A selected row whose column-0 item carries no path must also report, not fail silently."""
    screen = ReviewScreen()
    window = Mock()
    screen.connect_signals(window)
    screen._populate_recommendation_table(
        [
            RecommendationRow(
                position=1,
                title="Track",
                artist="Artist",
                bpm="128",
                camelot_key="8A",
                energy="7",
                spectral_color="",
                overall_score="—",
                path="",
            )
        ]
    )
    screen.recommendation_table.selectRow(0)

    screen._on_remove_clicked()

    window.status_label.setText.assert_called_once_with("Select a track in the playlist before removing it")
    window._library_controller.on_track_remove_requested.assert_not_called()


def test_double_click_without_path_reports_status(qapp: QApplication) -> None:
    """Double-clicking a row without a stored path must report, not fail silently."""
    screen = ReviewScreen()
    window = Mock()
    screen.connect_signals(window)
    screen._populate_recommendation_table(
        [
            RecommendationRow(
                position=1,
                title="Track",
                artist="Artist",
                bpm="128",
                camelot_key="8A",
                energy="7",
                spectral_color="",
                overall_score="—",
                path="",
            )
        ]
    )

    item = screen.recommendation_table.item(0, 0)
    assert item is not None
    screen._on_rec_double_clicked(item)

    window.status_label.setText.assert_called_once_with("That track has no playable file path")
    window._library_controller.on_track_play_requested.assert_not_called()


# ----------------------------------------------------------------------
# Per-track explainability on the Review screen (Plan 3 T4)
# ----------------------------------------------------------------------


def _recommendation_with_transitions(
    tracks: list[TrackRecord], transition_scores: list[TransitionScore]
) -> PlaylistRecommendation:
    return _recommendation(tracks).model_copy(update={"transition_scores": transition_scores})


def test_recommendation_rows_explain_why_each_track_is_listed(qapp: QApplication) -> None:
    """Each recommendation row tooltip states the track's role, metadata, and warnings.

    The DJ must see WHY a track is in the playlist without opening JSON exports.
    Only data that exists per-track is surfaced: position, opener/closer role,
    metadata completeness, and transition warnings touching the track.
    """
    tracks = [_track("/music/a.mp3"), _track("/music/b.mp3"), _track("/music/c.mp3")]
    warned_transition = TransitionScore(
        left_path="/music/a.mp3",
        right_path="/music/b.mp3",
        total_score=0.85,
        component_scores={"harmonic": 0.9},
        explanations=[],
        warnings=["BPM jump 6.2% exceeds threshold"],
    )
    state = AppState(
        scanned_records=tracks,
        last_recommendation=_recommendation_with_transitions(tracks, [warned_transition]),
    )

    screen = ReviewScreen()
    screen.render(ReviewViewModel(), state)

    opener_tip = screen.recommendation_table.item(0, 0).toolTip()
    assert "Track #1 of 3" in opener_tip
    assert "Playlist opener" in opener_tip
    assert "Metadata complete" in opener_tip
    assert "BPM jump 6.2% exceeds threshold" in opener_tip

    middle_tip = screen.recommendation_table.item(1, 0).toolTip()
    assert "Track #2 of 3" in middle_tip
    assert "BPM jump 6.2% exceeds threshold" in middle_tip

    closer_tip = screen.recommendation_table.item(2, 0).toolTip()
    assert "Track #3 of 3" in closer_tip
    assert "Playlist closer" in closer_tip
    assert "No warnings" in closer_tip


def test_track_reason_tooltip_reports_incomplete_metadata(qapp: QApplication) -> None:
    """A track with missing required metadata says so in its reason tooltip."""
    track = _track("/music/x.mp3").model_copy(
        update={"metadata_status": "incomplete", "missing_required_fields": ["bpm"]}
    )
    state = AppState(scanned_records=[track], last_recommendation=_recommendation([track]))

    screen = ReviewScreen()
    screen.render(ReviewViewModel(), state)

    tip = screen.recommendation_table.item(0, 0).toolTip()
    assert "Incomplete metadata" in tip
    assert "bpm" in tip


def test_track_reason_positions_skip_removed_tracks(qapp: QApplication) -> None:
    """Removed tracks disappear from the reasons and remaining positions renumber.

    The tooltip numbering must match the visible rows (the review view model
    renumbers positions after removals), otherwise the DJ sees "Track #3 of 3"
    on the second visible row.
    """
    tracks = [_track("/music/a.mp3"), _track("/music/b.mp3"), _track("/music/c.mp3")]
    state = AppState(
        scanned_records=tracks,
        last_recommendation=_recommendation(tracks),
        playlist_removed_paths=frozenset({"/music/a.mp3"}),
    )

    screen = ReviewScreen()
    screen.render(ReviewViewModel(), state)

    assert screen.recommendation_table.rowCount() == 2
    assert "Track #1 of 2" in screen.recommendation_table.item(0, 0).toolTip()
    assert "Track #2 of 2" in screen.recommendation_table.item(1, 0).toolTip()


def test_dj_readiness_summary_surfaces_the_energy_arc(qapp: QApplication) -> None:
    """The DJ readiness summary line states the energy arc from opener to closer."""
    tracks = [
        _track("/music/a.mp3").model_copy(update={"energy_level": 3}),
        _track("/music/b.mp3").model_copy(update={"energy_level": 7}),
    ]
    screen = ReviewScreen()
    controller = DjReadinessController(
        state=AppState(),
        review_screen=screen,
        sync_state=Mock(),
        last_report_setter=Mock(),
    )

    controller.show(
        _recommendation(tracks),
        RecommendationQualityReport(
            track_count=2,
            transition_count=1,
            average_transition_score=0.9,
            bpm_jumps=[],
            energy_jumps=[0],
            warning_count=0,
        ),
    )

    assert "Energy arc 3→7" in screen.dj_readiness_label.text()


def test_table_still_updates_when_rows_change(qapp: QApplication) -> None:
    """The signature cache must not freeze the table: changed rows still rebuild it."""
    screen = ReviewScreen()
    vm = ReviewViewModel()

    screen.render(vm, _state(["/music/a.mp3", "/music/b.mp3"]))
    screen.render(vm, _state(["/music/c.mp3"]))

    table = screen.recommendation_table
    assert table.rowCount() == 1
    assert table.item(0, 1).text() == "/music/c.mp3"


# ----------------------------------------------------------------------
# AI set narrative ("Explícame este set")
# ----------------------------------------------------------------------

_NARRATIVE = "El set abre calmo y cierra arriba."


def _review_state(paths: list[str], **overrides: object) -> AppState:
    """A ready-to-narrate review state, with anything overridden per test."""
    tracks = [_track(path) for path in paths]
    state = AppState(
        scanned_records=tracks,
        last_recommendation=_recommendation(tracks),
        last_dj_readiness_report=DjReadinessReport(
            status="ready",
            summary="Ready — 0 blocker(s), 0 review item(s); max BPM jump 2.00%",
            checks=[],
            blocker_count=0,
            review_count=0,
        ),
    )
    return state.model_copy(update=dict(overrides)) if overrides else state


def test_narrate_button_emits_the_request_signal(qapp: QApplication) -> None:
    """The button only announces intent: the window owns the request."""
    screen = ReviewScreen()
    vm = ReviewViewModel()
    requested: list[bool] = []
    screen.ai_narrate_requested.connect(lambda: requested.append(True))
    screen.render(vm, _review_state(["/music/a.mp3"]))

    screen.ai_narrate_button.click()

    assert requested == [True]


def test_narrate_button_and_narrative_display_are_accessible(qapp: QApplication) -> None:
    screen = ReviewScreen()

    assert screen.ai_narrate_button.objectName() == "ai_narrate_button"
    assert screen.ai_narrate_button.toolTip().strip()
    assert screen.ai_narrate_button.accessibleName().strip()
    assert screen.ai_narrative_label.accessibleName().strip()
    assert screen.ai_narrative_label.wordWrap()


def test_narrate_button_is_enabled_only_with_a_narratable_set(qapp: QApplication) -> None:
    """No recommendation, or no applied variant, means nothing honest to narrate yet."""
    screen = ReviewScreen()
    vm = ReviewViewModel()

    screen.render(vm, AppState())
    assert not screen.ai_narrate_button.isEnabled()

    screen.render(vm, _review_state(["/music/a.mp3", "/music/b.mp3"]))
    assert screen.ai_narrate_button.isEnabled()


def test_render_drives_the_narrate_busy_state(qapp: QApplication) -> None:
    """While narrating, the button is disabled and shows the busy label.

    Render-driven on purpose: the coalesced state sync walks the Review screen
    while the request is in flight, so an imperatively-set busy state would come
    back on the next sync.
    """
    screen = ReviewScreen()

    screen.render(ReviewViewModel(), _review_state(["/music/a.mp3"], is_narrating=True))

    assert not screen.ai_narrate_button.isEnabled()
    assert screen.ai_narrate_button.text() == "Narrando..."
    assert "Narrating the set" in screen.ai_narrate_status.text()

    screen.render(ReviewViewModel(), _review_state(["/music/a.mp3"]))

    assert screen.ai_narrate_button.isEnabled()
    assert screen.ai_narrate_button.text() == "Explícame este set"


def test_narrative_is_rendered_from_state_and_survives_rerenders(qapp: QApplication) -> None:
    """The narrative lives in state: an idle render must not wipe it."""
    screen = ReviewScreen()
    vm = ReviewViewModel()
    state = _review_state(["/music/a.mp3"], ai_narrative_text=_NARRATIVE)

    screen.render(vm, state)
    assert screen.ai_narrative_label.text() == _NARRATIVE
    assert screen.ai_narrative_label.isVisibleTo(screen)

    screen.render(vm, state)
    assert screen.ai_narrative_label.text() == _NARRATIVE
    assert screen.ai_narrative_label.isVisibleTo(screen)


def test_narrative_display_stays_hidden_until_there_is_something_to_show(qapp: QApplication) -> None:
    """An empty display must not eat the tables' vertical space (see the table-space guard)."""
    screen = ReviewScreen()

    screen.render(ReviewViewModel(), _review_state(["/music/a.mp3"]))

    assert screen.ai_narrative_label.text() == ""
    assert not screen.ai_narrative_label.isVisibleTo(screen)


def test_a_new_recommendation_clears_the_narrative_on_the_screen(qapp: QApplication) -> None:
    """The narrative describes one set; a replaced set must not keep narrating it."""
    screen = ReviewScreen()
    vm = ReviewViewModel()
    state = _review_state(["/music/a.mp3"], ai_narrative_text=_NARRATIVE)
    screen.render(vm, state)
    assert screen.ai_narrative_label.text() == _NARRATIVE

    replaced = _review_state(["/music/c.mp3"])
    screen.render(vm, replaced)

    assert screen.ai_narrative_label.text() == ""
    assert not screen.ai_narrative_label.isVisibleTo(screen)


def test_review_configure_and_cancel_are_real_clickable_actions(qapp: QApplication) -> None:
    from PySide6.QtTest import QTest

    screen = ReviewScreen()
    screen.show()
    configured: list[bool] = []
    cancelled: list[bool] = []
    screen.configure_ai_requested.connect(lambda: configured.append(True))
    screen.ai_narrate_cancel_requested.connect(lambda: cancelled.append(True))
    screen.render(ReviewViewModel(), _review_state(["/a", "/b"], is_narrating=True))
    QTest.mouseClick(screen.configure_ai_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(screen.ai_narrate_cancel_button, Qt.MouseButton.LeftButton)
    assert configured == [True]
    assert cancelled == [True]
    screen.render(ReviewViewModel(), _review_state(["/a", "/b"]))
    assert not screen.ai_narrate_cancel_button.isVisibleTo(screen)


def test_review_local_facts_toggle_works_with_ai_disabled(qapp: QApplication, monkeypatch) -> None:
    from PySide6.QtTest import QTest

    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    screen = ReviewScreen()
    screen.show()
    screen.render(ReviewViewModel(), _review_state(["/a", "/b"]))
    QTest.mouseClick(screen.engine_facts_button, Qt.MouseButton.LeftButton)
    assert screen.engine_facts_details.isVisibleTo(screen)
    assert "Local engine" in screen.engine_facts_details.toPlainText()
    assert "average transition score" in screen.engine_facts_details.toPlainText()
    screen.render(ReviewViewModel(), AppState())
    assert not screen.engine_facts_button.isEnabled()
    assert not screen.engine_facts_details.toPlainText()


def test_review_selected_replacement_is_preview_only_and_clears_on_change(qapp: QApplication) -> None:
    from PySide6.QtTest import QTest

    screen = ReviewScreen()
    screen.show()
    state = _review_state(["/a", "/b"], scanned_records=[_track("/alternative")])
    screen.render(ReviewViewModel(), state)
    item = screen.recommendation_table.item(1, 0)
    assert item is not None
    QTest.mouseClick(
        screen.recommendation_table.viewport(),
        Qt.MouseButton.LeftButton,
        pos=screen.recommendation_table.visualItemRect(item).center(),
    )
    QTest.mouseClick(screen.compare_replacement_button, Qt.MouseButton.LeftButton)
    assert "Original:" in screen.replacement_details.toPlainText()
    assert "Proposed:" in screen.replacement_details.toPlainText()
    assert "Preview only" in screen.replacement_details.toPlainText()
    assert [track.path for track in state.last_recommendation.ordered_tracks] == ["/a", "/b"]
    screen.render(ReviewViewModel(), _review_state(["/new-a", "/new-b"]))
    assert not screen.replacement_details.toPlainText()


def test_model_commentary_is_plain_text_even_for_html(qapp: QApplication) -> None:
    screen = ReviewScreen()
    narrative = '<img src="https://invalid.example/private">'
    screen.render(ReviewViewModel(), _review_state(["/a", "/b"], ai_narrative_text=narrative))
    assert screen.ai_narrative_label.textFormat() == Qt.TextFormat.PlainText
    assert screen.ai_narrative_label.text() == narrative


def test_empty_narrator_status_returns_its_height_to_tables(qapp: QApplication) -> None:
    screen = ReviewScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()
    tables = (screen.recommendation_table, screen.transition_table, screen.readiness_table)
    try:
        assert screen.ai_narrate_status.isHidden(), "empty status must not reserve a text row"
        idle_height = sum(table.height() for table in tables)
        for status in ("Narrating the set...", "Configure AI to retry.", "Set narrative ready."):
            screen.ai_narrate_status.setText(status)
            qapp.processEvents()
            assert screen.ai_narrate_status.isVisible()
            assert screen.ai_narrate_status.height() >= screen.ai_narrate_status.fontMetrics().height()
            assert sum(table.height() for table in tables) < idle_height
        screen.ai_narrate_status.setText("")
        qapp.processEvents()
        assert screen.ai_narrate_status.isHidden()
        assert sum(table.height() for table in tables) == idle_height
        assert idle_height > 0.65 * screen.height()
    finally:
        screen.close()
