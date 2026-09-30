from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication, QFrame

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.screens.build_screen import _COPILOT_COLUMNS, ANY_GENRE, BuildScreen
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, PrepCopilotVariant
from xfinaudio.recommendation.scoring import ScoringWeights
from xfinaudio.recommendation.strategies import PlaylistStrategy


def _unrouted(*_args: Any, **_kwargs: Any) -> Any:
    """Stand-in for the candidate routes this screen-level test never reaches."""
    return None


def _track(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
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


def _variant(
    name: str, tracks: list[TrackRecord], blockers: int = 0, pool_notes: tuple[str, ...] = ()
) -> PrepCopilotVariant:
    return PrepCopilotVariant(
        name=name,  # type: ignore[arg-type]
        description=f"Description for {name}",
        recommendation=_recommendation(tracks),
        readiness=DjReadinessReport(
            status="blocked" if blockers else "ready",  # type: ignore[arg-type]
            summary="Test",
            checks=[],
            blocker_count=blockers,
            review_count=0,
        ),
        warnings=[],
        blockers=["block!"] * blockers,
        pool_notes=pool_notes,
    )


def _plan_state(
    tracks: list[TrackRecord], blocked: frozenset[int] = frozenset(), pool_notes: tuple[str, ...] = ()
) -> AppState:
    """AppState carrying a three-variant copilot plan; *blocked* marks blocked variants."""
    variants = [
        _variant(name, tracks, blockers=1 if index in blocked else 0, pool_notes=pool_notes)
        for index, name in enumerate(("safe", "balanced", "adventurous"))
    ]
    return AppState(
        scanned_records=tracks,
        last_prep_copilot_plan=PrepCopilotPlan(intent=DJSetIntent(name="Test Set"), variants=variants),
    )


def test_recommend_progress_bar_shows_eta_and_hides_when_complete(qapp: QApplication) -> None:
    screen = BuildScreen()
    vm = BuildViewModel()

    screen.render(
        vm,
        AppState(
            is_recommending=True,
            recommend_progress_count=2,
            recommend_progress_total=5,
            recommend_elapsed_seconds=60,
        ),
        lightweight=True,
    )

    assert screen.recommend_progress_bar.isHidden() is False
    assert screen.recommend_progress_bar.value() == 40
    assert screen.recommend_progress_label.text() == "40% · 1:30 remaining"
    screen.render(vm, AppState(), lightweight=True)
    assert screen.recommend_progress_bar.isHidden() is True
    assert screen.recommend_progress_label.text() == ""


def test_primary_and_secondary_action_buttons_have_visual_hierarchy(qapp: QApplication) -> None:
    """Recommend is a larger primary action; Back is a smaller muted secondary action."""
    screen = BuildScreen()

    assert screen.recommend_button.objectName() == "primaryAction"
    assert screen.back_button.objectName() == "secondaryAction"
    assert screen.recommend_button.minimumHeight() > screen.back_button.maximumHeight()


def test_section_divider_separates_controls_from_table(qapp: QApplication) -> None:
    """A horizontal QFrame divider sits between the controls and the copilot table."""
    screen = BuildScreen()

    assert screen.section_divider.frameShape() == QFrame.Shape.HLine


def test_empty_state_shows_no_recommendation(qapp: QApplication) -> None:
    """Empty-state label guides the user while no recommendation exists."""
    screen = BuildScreen()
    vm = BuildViewModel()

    screen.render(vm, AppState(), lightweight=True)

    assert screen.empty_state_label.isHidden() is False
    assert "recommend" in screen.empty_state_label.text().casefold()


def test_all_buttons_have_tooltips(qapp: QApplication) -> None:
    """Every QPushButton on the screen exposes a non-empty tooltip (R1)."""
    from PySide6.QtWidgets import QPushButton

    screen = BuildScreen()

    buttons = screen.findChildren(QPushButton)
    assert buttons
    assert all(button.toolTip().strip() for button in buttons)


def test_copilot_table_headers_have_tooltips(qapp: QApplication) -> None:
    """Every copilot table column header carries an explanatory tooltip (R2)."""
    screen = BuildScreen()

    table = screen.copilot_table
    tooltips = [table.horizontalHeaderItem(col).toolTip() for col in range(table.columnCount())]
    assert all(tip.strip() for tip in tooltips)


def test_strategy_combo_shows_display_names_and_stores_internal_name_as_data(qapp: QApplication) -> None:
    """Combo items show display_name; itemData carries the internal strategy name.

    Spec `strategy-selection-ux` -> "Selector Shows Display Names".
    """
    screen = BuildScreen()
    vm = BuildViewModel()

    screen.render(vm, AppState(), lightweight=True)

    options = vm.available_strategies()
    assert screen.strategy_combo.count() == len(options)
    for index, option in enumerate(options):
        assert screen.strategy_combo.itemText(index) == option.display_name
        assert screen.strategy_combo.itemText(index) != option.name
        assert screen.strategy_combo.itemData(index) == option.name


def test_on_recommend_emits_internal_strategy_name_via_current_data(qapp: QApplication) -> None:
    """`_on_recommend` emits the internal strategy name (currentData), not the display label.

    Spec `strategy-selection-ux` -> "Selecting a display name resolves the internal strategy".
    """
    screen = BuildScreen()
    vm = BuildViewModel()
    screen.render(vm, AppState(), lightweight=True)

    target_index = screen.strategy_combo.findData("same_color_energy")
    assert target_index >= 0
    screen.strategy_combo.setCurrentIndex(target_index)

    emitted: list[str] = []
    screen.recommend_requested.connect(lambda strategy, _paths: emitted.append(strategy))

    screen._on_recommend()

    assert emitted == ["same_color_energy"]
    assert screen.strategy_combo.currentText() != "same_color_energy"


def test_strategy_explanation_label_refreshes_immediately_on_selection_change(qapp: QApplication) -> None:
    """The explanation label updates as soon as the combo selection changes, without a re-render.

    Spec `strategy-selection-ux` -> "Immediate Description Refresh on Selection".
    """
    screen = BuildScreen()
    vm = BuildViewModel()
    screen.render(vm, AppState(), lightweight=True)

    same_color_index = screen.strategy_combo.findData("same_color")
    same_color_energy_index = screen.strategy_combo.findData("same_color_energy")
    assert same_color_index >= 0
    assert same_color_energy_index >= 0

    screen.strategy_combo.setCurrentIndex(same_color_index)
    assert screen.strategy_explanation_label.text() == vm.strategy_explanation("same_color")

    screen.strategy_combo.setCurrentIndex(same_color_energy_index)

    assert screen.strategy_explanation_label.text() == vm.strategy_explanation("same_color_energy")


def test_selecting_strategy_by_display_name_resolves_to_internal_strategy_name(qapp: QApplication) -> None:
    """Selecting a combo item by its display label still resolves to the internal strategy name
    used for downstream generation and persistence/export.

    Spec `strategy-selection-ux` -> "Persisted and Exported Artifacts Record Internal Names".
    """
    from xfinaudio.recommendation.strategies import default_strategy_registry

    screen = BuildScreen()
    vm = BuildViewModel()
    screen.render(vm, AppState(), lightweight=True)

    display_label = "Same Color & Energy"
    index = screen.strategy_combo.findText(display_label)
    assert index >= 0
    screen.strategy_combo.setCurrentIndex(index)

    internal_name = screen.strategy_combo.currentData()
    assert internal_name == "same_color_energy"
    assert internal_name != display_label

    resolved = default_strategy_registry().get(internal_name)
    assert resolved.name == "same_color_energy"


def test_copilot_table_uses_the_free_vertical_space(qapp: QApplication) -> None:
    """A trailing addStretch(1) competed with the table for the free height.

    Measured at 1200x660: the table got 127px, about three visible rows, or 19%
    of the screen, while the spacer below it took the rest.
    """
    screen = BuildScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    table = screen.copilot_table
    row_height = max(table.verticalHeader().defaultSectionSize(), 1)

    # The screen carries a lot of controls above the table, so it will never own
    # most of the height; 127px was the spacer stealing what was left.
    assert table.viewport().height() // row_height >= 6
    assert table.height() > 0.33 * screen.height()


def test_copilot_description_column_is_wider_than_the_count_column(qapp: QApplication) -> None:
    """Description holds a sentence; Tracks holds a number. They were both 294px."""
    screen = BuildScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    header = screen.copilot_table.horizontalHeader()
    width = {name: header.sectionSize(index) for index, name in enumerate(_COPILOT_COLUMNS)}

    # A plain ">" would pass on the 294 vs 293 rounding of an even split.
    assert width["Description"] > 2 * width["Tracks"]
    assert width["Description"] > width["Readiness"]


def test_generate_with_no_tracks_keeps_the_copilot_signature_fresh(qapp: QApplication) -> None:
    """The controller's direct table clear must not leave a stale copilot signature.

    generate() with no selected tracks clears copilot_table directly. Without
    invalidating the cached row signature, a later render of identical variants
    skipped repopulation and left an empty table while the plan still held rows.
    """
    from xfinaudio.desktop.prep_copilot import PrepCopilotController

    screen = BuildScreen()
    vm = BuildViewModel()
    tracks = [_track("/a.flac"), _track("/b.flac")]
    state = _plan_state(tracks)

    screen.render(vm, state)
    assert screen.copilot_table.rowCount() == 3

    controller = PrepCopilotController(
        build_screen=screen,
        build_vm=vm,
        state=SimpleNamespace(
            _state=state,
            tr=lambda text: text,
            _selected_track_controls=lambda: None,
            _replace_app_state=lambda updated_state: None,
        ),
        workflow_service=object(),
        on_state_changed=lambda: None,
        on_status_message=lambda message: None,
        desktop_recommendation_records=_unrouted,
        desktop_color_anchor_candidate_context=_unrouted,
    )
    controller.generate()
    assert screen.copilot_table.rowCount() == 0

    # Identical variants come back after re-selecting tracks: the table must
    # repopulate instead of skipping on a signature cached before the clear.
    screen.render(vm, state)
    assert screen.copilot_table.rowCount() == 3


def test_copilot_tracks_cell_tooltip_shows_pool_notes(qapp: QApplication) -> None:
    """A DJ hovering the Tracks cell sees WHY the variant is small (no new columns)."""
    screen = BuildScreen()
    vm = BuildViewModel()
    tracks = [_track("/a.flac"), _track("/b.flac")]
    notes = ("Incoming pool: 10 track(s)", "Genre focus 'Classical': 10 -> 2 track(s)")

    screen.render(vm, _plan_state(tracks))
    assert screen.copilot_table.item(0, 2).toolTip() == ""

    screen.render(vm, _plan_state(tracks, pool_notes=notes))

    assert notes[0] in screen.copilot_table.item(0, 2).toolTip()
    assert notes[0] in screen.copilot_table.item(0, 3).toolTip()


def test_render_with_unchanged_rows_preserves_selection(qapp: QApplication) -> None:
    """Re-rendering the same copilot rows must not wipe the DJ's row selection."""
    screen = BuildScreen()
    vm = BuildViewModel()
    tracks = [_track("/a.flac"), _track("/b.flac")]

    screen.render(vm, _plan_state(tracks))
    assert screen.copilot_table.rowCount() == 3
    screen.copilot_table.selectRow(1)

    screen.render(vm, _plan_state(tracks))

    assert screen.copilot_table.selectedIndexes()
    assert screen.copilot_table.currentRow() == 1


def test_render_with_changed_rows_updates_table(qapp: QApplication) -> None:
    """A changed readiness status must still reach the table."""
    screen = BuildScreen()
    vm = BuildViewModel()
    tracks = [_track("/a.flac"), _track("/b.flac")]

    screen.render(vm, _plan_state(tracks))
    assert screen.copilot_table.item(0, 3).text() == "Ready"

    screen.render(vm, _plan_state(tracks, blocked=frozenset({0})))

    assert screen.copilot_table.item(0, 3).text() == "Blocked"


def test_render_with_changed_rows_restores_same_index_selection(qapp: QApplication) -> None:
    """When rows change but the count is stable, the same index stays selected."""
    screen = BuildScreen()
    vm = BuildViewModel()
    tracks = [_track("/a.flac"), _track("/b.flac")]

    screen.render(vm, _plan_state(tracks))
    screen.copilot_table.selectRow(1)

    screen.render(vm, _plan_state(tracks, blocked=frozenset({2})))

    assert screen.copilot_table.currentRow() == 1
    assert screen.copilot_table.selectedItems()


def test_apply_without_selection_reports_status(qapp: QApplication) -> None:
    """Applying with nothing selected must report guidance, not fail silently."""
    screen = BuildScreen()
    window = Mock()
    screen.connect_signals(window)

    screen._on_apply_variant()

    window.status_label.setText.assert_called_once_with("Generate and select a Prep Copilot variant before applying")


def test_anchor_genre_suggestion_selects_an_offered_genre(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])

    screen.suggest_genre_from_anchor("House")

    assert screen.genre_combo.currentText() == "House"


def test_anchor_genre_suggestion_leaves_selection_for_unavailable_or_missing_genre(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])
    screen.genre_combo.setCurrentText("Rock")

    screen.suggest_genre_from_anchor("Techno")
    assert screen.genre_combo.currentText() == "Rock"

    screen.suggest_genre_from_anchor(None)
    assert screen.genre_combo.currentText() == "Rock"


def test_programmatic_anchor_suggestions_do_not_count_as_a_dj_choice(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])

    screen.suggest_genre_from_anchor("House")
    screen.suggest_genre_from_anchor("Rock")

    assert screen.genre_combo.currentText() == "Rock"


def test_dj_genre_choice_wins_over_later_anchor_suggestions(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])
    any_genre_index = screen.genre_combo.findText(ANY_GENRE)
    screen.genre_combo.setCurrentIndex(any_genre_index)
    screen.genre_combo.activated.emit(any_genre_index)

    screen.suggest_genre_from_anchor("House")

    assert screen.genre_combo.currentText() == ANY_GENRE


def test_anchor_genre_suggestion_reports_the_pool_narrowing_in_the_status_label(qapp: QApplication) -> None:
    """An auto-applied anchor genre must not silently narrow the searched pool.

    The E2E run observed the combo switching from "Any genre" to the anchor's
    genre while the DJ believed the whole library was being searched (pool
    63 -> 4 with no explanation), so the change is reported to the status label.
    """
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])
    window = Mock()
    screen.connect_signals(window)

    screen.suggest_genre_from_anchor("House")

    assert screen.genre_combo.currentText() == "House"
    window.status_label.setText.assert_called_once_with(
        "Genre set to House from the anchor — switch back to Any genre to use the whole library"
    )


def test_anchor_genre_suggestion_does_not_re_report_the_same_genre(qapp: QApplication) -> None:
    """A second anchor pointing at the already-suggested genre stays silent."""
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])
    window = Mock()
    screen.connect_signals(window)

    screen.suggest_genre_from_anchor("House")
    screen.suggest_genre_from_anchor("House")

    window.status_label.setText.assert_called_once()


def test_dj_chosen_genre_never_triggers_the_anchor_genre_status_message(qapp: QApplication) -> None:
    """A DJ-made genre choice is never overridden and never reported as an anchor change."""
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])
    window = Mock()
    screen.connect_signals(window)
    any_genre_index = screen.genre_combo.findText(ANY_GENRE)
    screen.genre_combo.activated.emit(any_genre_index)

    screen.suggest_genre_from_anchor("House")

    window.status_label.setText.assert_not_called()
    assert screen.genre_combo.currentText() == ANY_GENRE


def test_copilot_tracks_cell_tooltip_shows_the_genre_prefilter_note(qapp: QApplication) -> None:
    """A prefilter shrink that ran before the plan must reach the tooltip too."""
    screen = BuildScreen()
    vm = BuildViewModel()
    tracks = [_track("/a.flac"), _track("/b.flac")]
    notes = ("Genre 'Disco' prefilter: 4 of 63 complete library track(s)", "Incoming pool: 4 track(s)")

    screen.render(vm, _plan_state(tracks, pool_notes=notes))

    assert notes[0] in screen.copilot_table.item(0, 2).toolTip()
    assert notes[0] in screen.copilot_table.item(0, 3).toolTip()


# ---------------------------------------------------------------------------
# AI copilot ask panel
# ---------------------------------------------------------------------------


def test_copilot_ask_request_is_emitted_by_the_button_and_the_return_key(qapp: QApplication) -> None:
    """One signal, two entry points: click and ReturnPressed both carry the typed request."""
    screen = BuildScreen()
    # The ask button is render-disabled until the library has tracks to plan from.
    screen.render(BuildViewModel(), _plan_state([_track("/a.flac")]))
    screen.copilot_ask_input.setText("45 minutes of deep house")
    emitted: list[str] = []
    screen.copilot_ask_requested.connect(emitted.append)

    screen.copilot_ask_button.click()
    screen.copilot_ask_input.returnPressed.emit()

    assert screen.copilot_ask_button.isEnabled() is True
    assert emitted == ["45 minutes of deep house", "45 minutes of deep house"]


def test_copilot_ask_panel_explains_itself_to_pointer_and_screen_reader_users(qapp: QApplication) -> None:
    screen = BuildScreen()

    assert screen.copilot_ask_input.placeholderText().strip()
    assert screen.copilot_ask_input.accessibleName().strip()
    assert screen.copilot_ask_button.accessibleName().strip()
    assert screen.copilot_ask_button.toolTip().strip()
    assert screen.copilot_ask_status.accessibleName().strip()
    assert screen.copilot_ask_status.wordWrap() is True
    assert screen.copilot_ask_status.maximumHeight() == 36
    # The theme styles by object name; an inline stylesheet would bypass it.
    assert screen.copilot_ask_button.styleSheet() == ""
    assert screen.copilot_ask_button.objectName() == "copilot_ask_button"


def test_render_owns_the_ask_button_enabled_state_while_a_request_is_busy(qapp: QApplication) -> None:
    """The 200ms render loop walks every screen, so the busy flag must drive the button."""
    screen = BuildScreen()
    vm = BuildViewModel()
    tracks = [_track("/a.flac")]
    busy = _plan_state(tracks).model_copy(update={"is_asking_copilot": True})

    screen.copilot_ask_button.setEnabled(True)
    screen.render(vm, busy)

    assert screen.copilot_ask_button.isEnabled() is False
    assert "copilot" in screen.copilot_ask_status.text().casefold()

    screen.render(vm, _plan_state(tracks))

    assert screen.copilot_ask_button.isEnabled() is True


def test_render_keeps_the_panel_message_written_by_the_controller(qapp: QApplication) -> None:
    """An idle render must not wipe the last failure/success guidance off the panel."""
    screen = BuildScreen()
    screen.copilot_ask_status.setText("AI copilot failed: connection reset")

    screen.render(BuildViewModel(), _plan_state([_track("/a.flac")]))

    assert screen.copilot_ask_status.text() == "AI copilot failed: connection reset"


def test_render_disables_the_ask_button_without_a_scanned_library(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.copilot_ask_button.setEnabled(True)

    screen.render(BuildViewModel(), AppState())

    assert screen.copilot_ask_button.isEnabled() is False


def test_fresh_visible_build_exposes_apply_and_inline_variant_details(qapp: QApplication) -> None:
    screen = BuildScreen()
    vm = BuildViewModel()
    screen.show()
    screen.render(vm, AppState(), lightweight=True)
    assert screen.apply_variant_button.isHidden()
    notes = ("Genre focus 'House': 10 -> 2 track(s)",)
    state = _plan_state([_track("/a.flac"), _track("/b.flac")], pool_notes=notes)

    screen.render(vm, state)
    qapp.processEvents()

    assert screen.copilot_table.isVisible()
    assert screen.apply_variant_button.isVisible()
    assert screen.copilot_table.currentRow() == 1
    assert screen.apply_variant_button.text() == "Use balanced · 2 tracks"
    assert "2 of 25 requested" in screen.variant_details_label.text()
    assert notes[0] in screen.variant_details_label.text()
    screen.copilot_table.selectRow(0)
    assert screen.apply_variant_button.text() == "Use safe · 2 tracks"
    screen.render(vm, state, lightweight=True)
    screen.render(vm, state)
    assert screen.copilot_table.currentRow() == 0
    screen.render(vm, AppState(), lightweight=True)
    assert screen.apply_variant_button.isHidden()
    assert screen.variant_details_label.isHidden()


def test_missing_anchor_has_visible_direct_next_step(qapp: QApplication) -> None:
    screen = BuildScreen()
    window = Mock()
    screen.connect_signals(window)
    vm = BuildViewModel()
    screen.render(vm, AppState(scanned_records=[_track("/complete.flac")]))
    assert not screen.copilot_button.isEnabled()
    assert screen.anchor_action_button.isVisibleTo(screen)
    assert screen.anchor_action_button.text() == "Choose a starting track"
    screen.anchor_action_button.click()
    window.workflow_tabs.setCurrentIndex.assert_called_with(0)
    screen.render(vm, AppState(scanned_records=[TrackRecord(path="/incomplete.flac")]))
    assert screen.anchor_action_button.text() == "Fix missing metadata"
    screen.anchor_action_button.click()
    window.workflow_tabs.setCurrentIndex.assert_called_with(5)
    tracks = [_track("/complete.flac")]
    screen.render(
        vm,
        AppState(
            scanned_records=tracks, records_by_path={tracks[0].path: tracks[0]}, selected_library_paths=[tracks[0].path]
        ),
    )
    assert screen.copilot_button.isEnabled()
    assert screen.anchor_action_button.isHidden()


def test_return_cannot_bypass_disabled_copilot_prerequisites(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.render(BuildViewModel(), AppState(scanned_records=[TrackRecord(path="/missing.flac")]))
    emitted: list[str] = []
    screen.copilot_ask_requested.connect(emitted.append)
    screen.copilot_ask_input.setText("A house set")
    screen.copilot_ask_input.returnPressed.emit()
    assert emitted == []
