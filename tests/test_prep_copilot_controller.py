from types import SimpleNamespace
from typing import Any

from xfinaudio.desktop.prep_copilot import PrepCopilotController


class _Index:
    def __init__(self, row: int) -> None:
        self._row = row

    def row(self) -> int:
        return self._row


class _Table:
    def selectedIndexes(self) -> list[_Index]:
        return [_Index(0)]

    def selectRow(self, row: int) -> None:
        self.selected = row

    def rowCount(self) -> int:
        return 1


def _label() -> Any:
    return SimpleNamespace(text="", tooltip="", setText=lambda text: None, setToolTip=lambda text: None)


class _State:
    def __init__(self, variant: Any) -> None:
        self._state = object()
        self.last_prep_copilot_plan = SimpleNamespace(variants=[variant])
        self._review_screen = SimpleNamespace(review_summary_label=_label(), dj_readiness_label=_label())
        self._export_screen = SimpleNamespace(export_guidance_label=_label())
        self.recommendation_calls: list[Any] = []
        self.transition_calls: list[Any] = []
        self.readiness_tables: list[Any] = []

    def tr(self, text: str) -> str:
        return text

    def _replace_app_state(self, updated_state: Any) -> None:
        self._state = updated_state

    def show_recommendation(self, tracks: Any, strategy_name: str, explanation: Any) -> None:
        self.recommendation_calls.append((tracks, strategy_name, explanation))

    def show_transition_review(self, explanation: Any) -> None:
        self.transition_calls.append(explanation)

    def _populate_dj_readiness_table(self, readiness: Any) -> None:
        self.readiness_tables.append(readiness)


def test_controller_delegates_selected_variant_application_to_injected_boundary(monkeypatch) -> None:
    strategy = SimpleNamespace(name="build")
    recommendation = SimpleNamespace(ordered_tracks=["track"], strategy=strategy)
    readiness = SimpleNamespace(summary="Ready — 0 blocker(s), 0 review item(s); max BPM jump 0.00%")
    quality_report = SimpleNamespace(
        track_count=1,
        transition_count=0,
        average_transition_score=0.0,
        warning_count=0,
    )
    variant = SimpleNamespace(name="balanced", recommendation=recommendation, readiness=readiness)
    application_result = SimpleNamespace(
        recommendation=recommendation,
        explanation=object(),
        quality_report=quality_report,
        readiness_report=readiness,
        variant_name="balanced",
    )
    build_screen = SimpleNamespace(copilot_table=_Table(), applied_copilot_variant_label=_label())
    state = _State(variant)
    builder_calls: list[Any] = []
    transition_calls: list[Any] = []
    status_messages: list[str] = []
    state_changes = 0

    def fake_apply_transition(state_arg, payload):
        transition_calls.append((state_arg, payload))
        return "updated-state"

    def on_state_changed() -> None:
        nonlocal state_changes
        state_changes += 1

    monkeypatch.setattr("xfinaudio.desktop.prep_copilot.apply_prep_copilot_variant", fake_apply_transition)
    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=object(),
        state=state,
        workflow_service=object(),
        on_state_changed=on_state_changed,
        on_status_message=status_messages.append,
        variant_application_builder=lambda variant_arg: builder_calls.append(variant_arg) or application_result,
    )

    controller.apply_selected_variant()

    assert builder_calls == [variant]
    assert transition_calls[0][1].quality_report is quality_report
    assert state._state == "updated-state"
    assert state_changes == 1
    assert state.recommendation_calls == [(recommendation.ordered_tracks, "build", application_result.explanation)]
    assert state.transition_calls == [application_result.explanation]
    assert state.readiness_tables == [readiness]
    assert status_messages == ["Applied Prep Copilot variant: balanced"]
