"""Local Review facts and comparisons never require a provider."""

from tests.test_ai_narrator_controller import _readiness, _recommendation, _track
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.review_assistance import review_engine_facts
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, PrepCopilotVariant


def _state() -> AppState:
    recommendation = _recommendation([_track("/a"), _track("/b")])
    return AppState(last_recommendation=recommendation, last_dj_readiness_report=_readiness())


def _plan(state: AppState) -> PrepCopilotPlan:
    PrepCopilotVariant.model_rebuild(_types_namespace={"DjReadinessReport": DjReadinessReport})
    assert state.last_recommendation is not None
    return PrepCopilotPlan(
        intent=DJSetIntent(name="Test"),
        variants=[
            PrepCopilotVariant(
                name="safe",
                description="Synthetic",
                recommendation=state.last_recommendation,
                readiness=_readiness(),
                warnings=[],
                blockers=[],
            )
        ],
    )


def test_local_facts_describe_scores_risks_and_readiness() -> None:
    state = _state()
    text = review_engine_facts(state)
    assert "0.80" in text
    assert "0 blocker" in text
    assert "Transition 1" in text
    assert "No alternative" in text
    assert review_engine_facts(AppState()) == ""


def test_comparison_only_uses_current_engine_plan() -> None:
    state = _state()
    state = state.model_copy(update={"last_prep_copilot_plan": _plan(state)})
    assert "safe: 2 tracks" in review_engine_facts(state)
    new_set = _recommendation([_track("/c"), _track("/d")])
    state = state.model_copy(update={"last_recommendation": new_set})
    assert "safe: 2 tracks" not in review_engine_facts(state)


def test_comparison_omits_alternatives_conflicting_with_current_controls() -> None:
    state = _state()
    plan = _plan(state)
    for controls in ({"excluded_paths": frozenset({"/a"})}, {"locked_paths": frozenset({"/missing"})}):
        text = review_engine_facts(state.model_copy(update={"last_prep_copilot_plan": plan, **controls}))
        assert "safe: 2 tracks" not in text
