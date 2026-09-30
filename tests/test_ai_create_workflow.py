"""Confirmation-first Create with real widgets and synthetic worker boundaries."""

from types import SimpleNamespace

import pytest

from xfinaudio.ai import NanConfigError
from xfinaudio.desktop.ai_copilot import AiCopilotController
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.screens.build_screen import BuildScreen
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan


@pytest.fixture
def workflow(qapp, monkeypatch):
    screen = BuildScreen()
    tracks = [
        TrackRecord(
            path=p, title=p, genre="House", bpm=124, camelot_key="8A", energy_level=5, metadata_status="complete"
        )
        for p in ("a", "b", "c")
    ]
    controls = DJControls(locked_paths={"a"}, excluded_paths={"c"})
    host = SimpleNamespace(
        _state=AppState(scanned_records=tracks), tr=lambda value: value, _selected_track_controls=lambda: controls
    )
    jobs, plans = [], []
    intent = DJSetIntent(name="House", target_minutes=30, genre_focus="House")

    def builder(records, requested, **kwargs):
        plans.append((records, requested, kwargs))
        return PrepCopilotPlan(intent=requested, variants=[])

    controller = AiCopilotController(
        build_screen=screen,
        build_vm=BuildViewModel(),
        state=host,
        on_state_changed=lambda: None,
        desktop_recommendation_records=lambda *a, **kw: tracks,
        desktop_color_anchor_candidate_context=lambda *a, **kw: None,
        intent_extractor=lambda *a, **kw: intent,
        plan_generation_builder=builder,
    )
    monkeypatch.setattr(controller, "_start_worker", lambda operation, rid: jobs.append((operation, rid)))
    screen.copilot_ask_requested.connect(controller.ask)
    screen.render(BuildViewModel(), host._state)
    screen.copilot_ask_input.setText("House for 30 minutes")

    def finish(index):
        operation, rid = jobs[index]
        try:
            controller._on_worker_finished(operation(), rid)
        except Exception as error:
            controller._on_worker_failed(error, rid)

    yield SimpleNamespace(screen=screen, controller=controller, host=host, jobs=jobs, plans=plans, finish=finish)
    controller.cancel()
    screen.close()


def test_confirmation_is_required_before_local_generation_and_apply(workflow):
    w = workflow
    w.screen.copilot_ask_button.click()
    assert w.host._state.is_asking_copilot
    w.finish(0)
    assert not w.host._state.is_asking_copilot
    assert not w.screen.intent_preview.isHidden()
    assert "1 locked" in w.screen.intent_preview.constraints.text()
    assert not w.plans and w.host._state.last_prep_copilot_plan is None
    w.screen.intent_preview.duration.setValue(45)
    w.screen.intent_preview.confirm_button.click()
    assert len(w.jobs) == 2 and not w.plans
    w.finish(1)
    assert w.plans[0][1].target_minutes == 45
    assert w.plans[0][1].required_paths == ["a"]
    assert w.plans[0][1].excluded_paths == {"c"}
    assert w.host._state.last_prep_copilot_plan is not None
    assert w.host._state.last_recommendation is None


def test_cancel_discards_late_results_and_retry_is_reachable(workflow):
    w = workflow
    w.screen.copilot_ask_button.click()
    w.screen.copilot_cancel_button.click()
    w.finish(0)
    assert w.screen.intent_preview.isHidden()
    assert not w.host._state.is_asking_copilot
    w.screen.copilot_ask_button.click()
    w.finish(1)
    assert not w.screen.intent_preview.isHidden()
    w.screen.intent_preview.edit_button.click()
    assert w.screen.intent_preview.isHidden()
    assert not w.plans


def test_changed_library_rejects_stale_confirmation(workflow):
    w = workflow
    w.screen.copilot_ask_button.click()
    w.finish(0)
    w.host._state = w.host._state.model_copy(update={"scanned_records": []})
    w.screen.intent_preview.confirm_button.click()
    assert not w.plans and len(w.jobs) == 1
    assert "changed" in w.screen.copilot_ask_status.text()


def test_generation_result_after_constraints_change_is_not_published(workflow):
    w = workflow
    w.screen.copilot_ask_button.click()
    w.finish(0)
    w.screen.intent_preview.confirm_button.click()
    w.host._selected_track_controls = lambda: DJControls(excluded_paths={"b"})
    w.finish(1)
    assert w.host._state.last_prep_copilot_plan is None
    assert "changed" in w.screen.copilot_ask_status.text()


def test_configuration_failure_exposes_action_and_allows_retry(workflow):
    w = workflow
    w.screen.copilot_ask_button.click()
    w.controller._on_worker_failed(NanConfigError("disabled"), w.jobs[0][1])
    assert w.screen.copilot_configure_button.isEnabled()
    assert "Configure AI" in w.screen.copilot_ask_status.text()
    assert w.screen.copilot_ask_button.isEnabled()
