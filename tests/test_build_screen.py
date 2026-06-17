from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame, QHeaderView

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.screens.build_screen import BuildScreen
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, PrepCopilotVariant
from xfinaudio.recommendation.scoring import ScoringWeights
from xfinaudio.recommendation.strategies import PlaylistStrategy


def _state_with_long_descriptions() -> AppState:
    track = TrackRecord(path="/a.flac", bpm=128.0, camelot_key="8A", energy_level=7, metadata_status="complete")
    recommendation = PlaylistRecommendation(
        ordered_tracks=[track],
        transition_scores=[],
        strategy=PlaylistStrategy(
            name="harmonic_journey",
            display_name="Harmonic Journey",
            description="Test",
            weights=ScoringWeights(),
        ),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )
    long_description = (
        "Strictest option: stays close to the requested anchor energy and key, only allowing "
        "transitions that keep the Camelot wheel adjacent and BPM within a tight tolerance band."
    )
    variant = PrepCopilotVariant(
        name="safe",  # type: ignore[arg-type]
        description=long_description,
        recommendation=recommendation,
        readiness=DjReadinessReport(status="ready", summary="ok", checks=[], blocker_count=0, review_count=0),
        warnings=[],
        blockers=[],
    )
    plan = PrepCopilotPlan(intent=DJSetIntent(name="Set"), variants=[variant])
    return AppState(last_prep_copilot_plan=plan)


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


def test_copilot_description_column_stretches_and_others_fit_contents(qapp: QApplication) -> None:
    """Description gets the flexible space; other columns size to their content (no cut-off)."""
    screen = BuildScreen()
    header = screen.copilot_table.horizontalHeader()

    assert header.sectionResizeMode(1) == QHeaderView.ResizeMode.Stretch
    for col in (0, 2, 3):
        assert header.sectionResizeMode(col) == QHeaderView.ResizeMode.ResizeToContents


def test_copilot_description_wraps_and_exposes_full_text_tooltip(qapp: QApplication) -> None:
    """A long variant description wraps onto multiple lines and the full text is in the tooltip."""
    screen = BuildScreen()
    vm = BuildViewModel()
    state = _state_with_long_descriptions()

    screen.render(vm, state, lightweight=False)

    assert screen.copilot_table.wordWrap() is True
    description_item = screen.copilot_table.item(0, 1)
    assert description_item is not None
    full_text = state.last_prep_copilot_plan.variants[0].description
    assert description_item.text() == full_text
    assert description_item.toolTip() == full_text


def test_genre_cohesion_slider_emits_and_reports_value(qapp: QApplication) -> None:
    """A Genre Cohesion slider mirrors the Spectral Cohesion control (0-100)."""
    screen = BuildScreen()
    emitted: list[int] = []
    screen.genre_cohesion_changed.connect(emitted.append)

    screen.genre_cohesion_slider.setValue(60)

    assert screen.genre_cohesion_value() == 60
    assert emitted == [60]
    assert screen.genre_cohesion_value_label.text() == "60%"


def test_guidance_labels_are_grouped_in_a_panel(qapp: QApplication) -> None:
    """The recommendation/constraint/summary guidance labels share one panel container."""
    screen = BuildScreen()
    panel = screen.build_guidance_panel
    assert isinstance(panel, QFrame)
    for label in (
        screen.recommendation_vs_copilot_label,
        screen.constraint_explanation_label,
        screen.recommendation_summary_label,
    ):
        assert panel.isAncestorOf(label)
