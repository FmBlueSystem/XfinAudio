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


def test_selected_replacement_is_engine_preview_and_never_mutates_state() -> None:
    from xfinaudio.desktop.review_assistance import preview_engine_replacement

    state = _state()
    candidate = _track("/candidate").model_copy(update={"title": "Alternative", "genre": "House"})
    state = state.model_copy(update={"scanned_records": [candidate]})
    before = state.last_recommendation
    text = preview_engine_replacement(state, "/b")
    assert "Alternative" in text
    assert "Original" in text and "Proposed" in text
    assert "score" in text and "review" in text.lower()
    assert state.last_recommendation is before
    assert [track.path for track in before.ordered_tracks] == ["/a", "/b"]


def test_replacement_preview_refuses_protected_excluded_and_unknown_choices() -> None:
    from xfinaudio.desktop.review_assistance import preview_engine_replacement

    state = _state().model_copy(update={"scanned_records": [_track("/candidate")]})
    assert "protected" in preview_engine_replacement(state.model_copy(update={"locked_paths": frozenset({"/b"})}), "/b")
    assert "No eligible" in preview_engine_replacement(
        state.model_copy(update={"excluded_paths": frozenset({"/candidate"})}), "/b"
    )
    assert "Select" in preview_engine_replacement(state, "/unknown")
    assert "Select" in preview_engine_replacement(AppState(), "/b")
    manual = state.last_recommendation.model_copy(update={"applied_controls": {"manual_order_paths": ["/a", "/b"]}})
    assert "protected" in preview_engine_replacement(state.model_copy(update={"last_recommendation": manual}), "/b")
