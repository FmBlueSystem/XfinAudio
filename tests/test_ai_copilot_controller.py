"""Offline controller tests for the AI copilot panel.

Nothing here touches the network or a real widget: the intent extractor, the plan
builder and the two candidate routes are injected, the request body is a fixed
DJSetIntent, and the worker boundary is captured instead of spawning a thread.
The single test that lets the real QThread run only does so to prove the blocking
extraction left the UI thread -- the extractor itself is still a fake.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtCore import QThread

from xfinaudio.ai import NanConfigError, extract_intent
from xfinaudio.application.recommendation_candidates import RecommendationCandidateContext
from xfinaudio.config.settings import AppSettings, LoudnessSettings
from xfinaudio.desktop.ai_copilot import AI_COPILOT_TIMEOUT_SECONDS, AiCopilotController
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.app_state_transitions import (
    apply_ai_copilot_request_finished,
    apply_ai_copilot_request_started,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.loudness_policy import LoudnessBand
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan

_INTENT = DJSetIntent(
    name="Deep house opener",
    strategy="harmonic_journey",
    target_track_count=18,
    genre_focus="House",
)


def _track(path: str) -> TrackRecord:
    return TrackRecord(path=path, title=path, metadata_status="complete")


class _Label:
    """Minimal QLabel double: the panel status line."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    def setText(self, text: str) -> None:  # noqa: N802 - Qt-compatible test double
        self.texts.append(text)

    @property
    def text(self) -> str:
        return self.texts[-1] if self.texts else ""


class _AskScreen:
    """Build-screen double exposing only the AI panel surface the controller owns.

    There is deliberately no strategy combo or target-count input: the AI request
    must never read the DJ's manual set-shape controls, so touching them would
    raise here instead of silently coupling the two entry points.
    """

    def __init__(self) -> None:
        self.copilot_ask_status = _Label()
        self.apply_variant_states: list[bool] = []
        self.apply_variant_button = SimpleNamespace(setEnabled=self.apply_variant_states.append)
        self.renders: list[AppState] = []

    def render(self, _vm: Any, state: AppState) -> None:
        self.renders.append(state)


class _StateHost:
    """MainWindow double: the controller reaches AppState through it, like Prep Copilot."""

    def __init__(self, *, library: list[TrackRecord], controls: Any = None) -> None:
        self._state = AppState(scanned_records=library)
        self._controls = controls
        self.settings = AppSettings(loudness=LoudnessSettings(target_lufs=-14.0, tolerance_lu=0.5))

    def tr(self, text: str) -> str:
        return text

    def _selected_track_controls(self) -> Any:
        return self._controls

    def _replace_app_state(self, updated: AppState) -> None:
        self._state = updated


class _Harness:
    """Wire the controller with captured seams instead of a live worker thread."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        library: list[TrackRecord] | None = None,
        controls: Any = None,
        extractor: Any = None,
        capture_worker: bool = True,
    ) -> None:
        self.main_thread = threading.current_thread()
        self.host = _StateHost(library=[_track("/music/a.flac")] if library is None else library, controls=controls)
        self.screen = _AskScreen()
        self.intent = _INTENT
        self.plan = SimpleNamespace(variants=[object(), object(), object()])
        self.pool = [_track("/music/pool.flac")]
        self.extractor_calls: list[tuple[str, list[TrackRecord], float]] = []
        self.route_calls: list[tuple[Any, str | None, LoudnessBand]] = []
        self.builder_calls: list[tuple[Any, Any, str | None, LoudnessBand]] = []
        self.state_changes: list[threading.Thread] = []
        self.jobs: list[tuple[Any, int]] = []

        def default_extractor(request: str, tracks: list[TrackRecord], *, timeout: float) -> DJSetIntent:
            self.extractor_calls.append((request, tracks, timeout))
            return self.intent

        def records_route(controls_arg: Any, strategy_name: str | None, *, loudness_band: LoudnessBand) -> Any:
            self.route_calls.append((controls_arg, strategy_name, loudness_band))
            return self.pool

        def color_route(controls_arg: Any, strategy_name: str, *, loudness_band: LoudnessBand) -> Any:
            self.route_calls.append((controls_arg, strategy_name, loudness_band))
            return SimpleNamespace(records=self.pool, color_anchor_path="/music/anchor.flac")

        def plan_builder(
            tracks: Any,
            intent: Any,
            *,
            color_anchor_path: str | None = None,
            loudness_band: LoudnessBand,
        ) -> Any:
            self.builder_calls.append((tracks, intent, color_anchor_path, loudness_band))
            return self.plan

        chosen_extractor: Any = extractor if extractor is not None else default_extractor
        self.controller = AiCopilotController(
            build_screen=self.screen,
            build_vm=object(),
            state=self.host,
            on_state_changed=self._on_state_changed,
            desktop_recommendation_records=records_route,
            desktop_color_anchor_candidate_context=color_route,
            intent_extractor=chosen_extractor,
            plan_generation_builder=plan_builder,
        )
        if capture_worker:
            monkeypatch.setattr(AiCopilotController, "_start_worker", self._capture_worker)

    def _on_state_changed(self) -> None:
        self.state_changes.append(threading.current_thread())

    def _capture_worker(self, operation: Any, request_id: int) -> None:
        self.jobs.append((operation, request_id))

    def run(self, index: int = 0) -> None:
        """Run one captured job and route it back exactly like BackgroundWorker does."""
        operation, request_id = self.jobs[index]
        try:
            result = operation()
        except Exception as exc:
            self.controller._on_worker_failed(exc, request_id)
        else:
            self.controller._on_worker_finished(result, request_id)


# ---------------------------------------------------------------------------
# Request lifecycle
# ---------------------------------------------------------------------------


def test_ask_marks_the_request_busy_then_stores_the_generated_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _Harness(monkeypatch)
    library = list(harness.host._state.scanned_records)

    harness.controller.ask("  Deep house opener  ")

    assert harness.host._state.is_asking_copilot is True
    assert harness.host._state.ai_copilot_request == "Deep house opener"
    assert harness.screen.renders[-1].is_asking_copilot is True
    assert harness.state_changes
    assert harness.jobs and len(harness.jobs) == 1
    # The blocking network call is handed to the worker, never run in the slot.
    assert harness.extractor_calls == []

    harness.run()
    assert harness.host._state.last_prep_copilot_plan is None
    harness.controller.confirm()
    harness.run(1)

    assert harness.extractor_calls == [("Deep house opener", library, AI_COPILOT_TIMEOUT_SECONDS)]
    assert harness.host._state.is_asking_copilot is False
    assert harness.host._state.last_prep_copilot_plan is harness.plan
    assert harness.screen.apply_variant_states == [True]
    assert harness.screen.copilot_ask_status.text == "AI copilot generated 3 Prep Copilot variant(s)"
    assert harness.screen.renders[-1].last_prep_copilot_plan is harness.plan
    assert harness.state_changes[-1] is harness.main_thread


def test_ask_plans_with_the_ai_intent_and_the_candidate_route_never_the_ui_combos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The LLM fills the intent; the pool and the plan come from the injected seams."""
    controls = DJControls(start_path="/music/a.flac")
    harness = _Harness(monkeypatch, controls=controls)

    harness.controller.ask("deep house")
    harness.run()
    harness.controller.confirm()
    harness.run(1)

    band = LoudnessBand(-14.0, 0.5)
    assert harness.route_calls == [(controls, "harmonic_journey", band)]
    assert harness.builder_calls == [
        (harness.pool, _INTENT.model_copy(update={"start_path": controls.start_path}), None, band)
    ]


def test_ask_plans_from_the_library_when_the_dj_selected_no_track(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _Harness(monkeypatch, controls=None)

    harness.controller.ask("deep house")
    harness.run()
    harness.controller.confirm()
    harness.run(1)

    assert harness.route_calls == [(None, "harmonic_journey", LoudnessBand(-14.0, 0.5))]
    assert harness.host._state.last_prep_copilot_plan is harness.plan


def test_ask_is_ignored_while_a_request_is_already_in_flight(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _Harness(monkeypatch)

    harness.controller.ask("first")
    harness.controller.ask("second")

    assert len(harness.jobs) == 1
    assert harness.host._state.ai_copilot_request == "first"
    assert len(harness.screen.renders) == 1


@pytest.mark.parametrize("typed_request", ["", "   "], ids=["empty", "blank"])
def test_ask_without_a_request_reports_guidance(monkeypatch: pytest.MonkeyPatch, typed_request: str) -> None:
    harness = _Harness(monkeypatch)

    harness.controller.ask(typed_request)

    assert harness.jobs == []
    assert harness.host._state.is_asking_copilot is False
    assert "Describe the set" in harness.screen.copilot_ask_status.text


def test_ask_without_a_scanned_library_reports_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _Harness(monkeypatch, library=[])

    harness.controller.ask("deep house")

    assert harness.jobs == []
    assert "Scan your library" in harness.screen.copilot_ask_status.text


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (NanConfigError("API key file not found: /keys/apiIA.env"), "AI copilot is not configured"),
        (ValueError("LLM did not return a JSON object: 'noise'."), "AI copilot could not understand the request"),
        (RuntimeError("connection reset"), "AI copilot failed: connection reset"),
    ],
    ids=["nan-config", "value-error", "unexpected"],
)
def test_extractor_failures_clear_the_busy_flag_and_report_on_the_panel(
    monkeypatch: pytest.MonkeyPatch, error: Exception, expected: str
) -> None:
    """Every failure shape lands on the panel status line: no modal, no stuck button."""

    def failing(*_args: Any, **_kwargs: Any) -> Any:
        raise error

    harness = _Harness(monkeypatch, extractor=failing)

    harness.controller.ask("deep house")
    harness.run()

    assert harness.host._state.is_asking_copilot is False
    assert harness.host._state.last_prep_copilot_plan is None
    assert expected in harness.screen.copilot_ask_status.text
    assert harness.screen.renders[-1].is_asking_copilot is False
    assert harness.screen.apply_variant_states == []


def test_late_worker_results_do_not_override_a_newer_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """A superseded request must not clear the busy flag or overwrite the newer plan."""
    harness = _Harness(monkeypatch)

    harness.controller.ask("first")
    harness.run()
    harness.controller.confirm()
    harness.run(1)
    assert harness.host._state.last_prep_copilot_plan is harness.plan

    stale_plan = SimpleNamespace(variants=[object()])
    harness.controller.ask("second")
    assert harness.host._state.is_asking_copilot is True

    harness.controller._on_worker_finished(stale_plan, 1)
    harness.controller._on_worker_failed(RuntimeError("late failure"), 1)

    assert harness.host._state.is_asking_copilot is True
    assert harness.host._state.last_prep_copilot_plan is harness.plan

    harness.run(2)
    assert harness.host._state.is_asking_copilot is False


def test_nan_config_failure_points_at_the_settings_toggle_and_the_key_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guidance, not just diagnosis: where to enable AI, that it applies without restart, and the key file."""

    def failing(*_args: Any, **_kwargs: Any) -> Any:
        raise NanConfigError("API key file not found: /keys/apiIA.env")

    harness = _Harness(monkeypatch, extractor=failing)

    harness.controller.ask("deep house")
    harness.run()

    text = harness.screen.copilot_ask_status.text
    assert "Settings" in text
    assert "Configure AI" in text
    assert "restart" not in text
    assert "API key file" in text


# ---------------------------------------------------------------------------
# Threading and seams
# ---------------------------------------------------------------------------


def test_ask_runs_the_blocking_extractor_off_the_ui_thread(monkeypatch: pytest.MonkeyPatch, qapp: Any) -> None:
    """extract_intent is a blocking network call, so it must not run in the slot."""
    worker_threads: list[threading.Thread] = []
    release = threading.Event()

    def slow_extractor(_request: str, _tracks: Any, *, timeout: float) -> DJSetIntent:
        worker_threads.append(threading.current_thread())
        release.wait(5)
        return _INTENT

    harness = _Harness(monkeypatch, extractor=slow_extractor, capture_worker=False)
    try:
        harness.controller.ask("deep house")
        assert harness.host._state.is_asking_copilot is True
        assert harness.screen.renders[-1].is_asking_copilot is True

        deadline = time.monotonic() + 5
        while not worker_threads and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        assert worker_threads, "the worker never picked up the request"
        assert worker_threads[0] is not harness.main_thread

        release.set()
        while harness.controller._pending_intent is None and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        assert harness.host._state.last_prep_copilot_plan is None
        harness.controller.confirm()
        while harness.host._state.last_prep_copilot_plan is None and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

        assert harness.host._state.last_prep_copilot_plan is harness.plan
        assert harness.host._state.is_asking_copilot is False
        assert harness.state_changes[-1] is harness.main_thread
        assert harness.screen.copilot_ask_status.text == "AI copilot generated 3 Prep Copilot variant(s)"
    finally:
        release.set()
        harness.controller.cancel()
        deadline = time.monotonic() + 5
        while harness.controller._copilot_thread is not None and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)


def test_controller_defaults_bind_the_real_extractor_and_plan_builder() -> None:
    controller = AiCopilotController(
        build_screen=_AskScreen(),
        build_vm=object(),
        state=_StateHost(library=[_track("/music/a.flac")]),
        on_state_changed=lambda: None,
        desktop_recommendation_records=lambda *_args, **_kwargs: [],
        desktop_color_anchor_candidate_context=lambda *_args, **_kwargs: RecommendationCandidateContext(),
    )

    assert controller._intent_extractor is extract_intent
    assert controller._plan_generation_builder is build_prep_copilot_plan


def test_state_replacement_supports_a_host_without_its_own_replacer(monkeypatch: pytest.MonkeyPatch) -> None:
    """The controller works with either host shape, like the Prep Copilot controller does."""
    harness = _Harness(monkeypatch)
    bare_host = SimpleNamespace(
        _state=harness.host._state,
        tr=lambda text: text,
        settings=harness.host.settings,
        _selected_track_controls=lambda: None,
    )
    harness.controller._state = bare_host

    harness.controller.ask("deep house")

    assert bare_host._state.is_asking_copilot is True


def test_cancel_interrupts_a_running_worker_and_is_safe_without_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """closeEvent cancels the in-flight request; an idle panel must not raise."""
    interrupted: list[bool] = []
    waits: list[int] = []

    class _Thread:
        def isRunning(self) -> bool:  # noqa: N802 - QThread-compatible test double
            return True

        def requestInterruption(self) -> None:  # noqa: N802 - QThread-compatible test double
            interrupted.append(True)

        def wait(self, milliseconds: int) -> bool:  # noqa: N802 - QThread-compatible test double
            waits.append(milliseconds)
            return True

    harness = _Harness(monkeypatch)
    harness.controller.cancel()

    assert interrupted == []

    harness.controller._copilot_thread = cast(Any, _Thread())
    harness.controller.cancel()

    assert interrupted == [True]
    assert waits == []


def test_a_superseded_thread_does_not_clear_the_current_worker_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old thread finishes after the DJ asked again; its cleanup must not win."""
    harness = _Harness(monkeypatch)
    current_thread = QThread()
    stale_thread = QThread()
    harness.controller._copilot_thread = current_thread
    harness.controller._copilot_worker = cast(Any, object())
    monkeypatch.setattr(harness.controller, "sender", lambda: stale_thread, raising=False)

    harness.controller._on_worker_cleared()

    assert harness.controller._copilot_thread is current_thread
    assert harness.controller._copilot_worker is not None

    monkeypatch.setattr(harness.controller, "sender", lambda: current_thread, raising=False)
    harness.controller._on_worker_cleared()

    assert harness.controller._copilot_thread is None
    assert harness.controller._copilot_worker is None


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


def test_ai_copilot_transitions_track_the_in_flight_request() -> None:
    state = AppState()

    started = apply_ai_copilot_request_started(state, "deep house")

    assert started is not state
    assert started.is_asking_copilot is True
    assert started.ai_copilot_request == "deep house"
    assert state.is_asking_copilot is False

    finished = apply_ai_copilot_request_finished(started)

    assert finished.is_asking_copilot is False
    assert finished.ai_copilot_request == "deep house"
    assert started.is_asking_copilot is True
