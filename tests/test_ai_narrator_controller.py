"""Offline controller tests for the "Explícame este set" AI narrator.

Nothing here touches the network or a real widget: the narrator seam is injected,
the recommendation and readiness are fixed fixtures, and the worker boundary is
captured instead of spawning a thread. The single test that lets the real QThread
run only does so to prove the blocking call left the UI thread -- the narrator
itself is still a fake.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtCore import QThread

from xfinaudio.ai import NanConfigError, narrate_set
from xfinaudio.desktop.ai_narrator import AI_NARRATOR_TIMEOUT_SECONDS, AiNarratorController
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.app_state_transitions import (
    apply_ai_narrative_cleared,
    apply_ai_narrative_finished,
    apply_ai_narrative_started,
    apply_prep_copilot_variant,
    apply_recommendation_completion,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import ScoringWeights, TransitionScore
from xfinaudio.recommendation.strategies import PlaylistStrategy

NARRATIVE = "El set abre calmo y cierra arriba."


def _track(path: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        artist="Test Artist",
        bpm=124.0,
        camelot_key="8A",
        energy_level=6,
        metadata_status="complete",
    )


def _recommendation(tracks: list[TrackRecord]) -> PlaylistRecommendation:
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[
            TransitionScore(
                left_path=tracks[0].path,
                right_path=tracks[1].path,
                total_score=0.8,
                component_scores={},
                explanations=[],
                warnings=[],
            )
        ]
        if len(tracks) > 1
        else [],
        strategy=PlaylistStrategy(
            name="harmonic_journey",
            display_name="Harmonic Journey",
            description="Test strategy",
            weights=ScoringWeights(),
        ),
        warnings=[],
        applied_controls={},
        optimizer="test-optimizer",
        total_score=0.8,
    )


def _readiness() -> DjReadinessReport:
    return DjReadinessReport(
        status="ready",
        summary="Ready — 0 blocker(s), 0 review item(s); max BPM jump 2.00%",
        checks=[DjReadinessCheck(label="Metadata", status="ready", detail="Complete")],
        blocker_count=0,
        review_count=0,
    )


def _ready_state(tracks: list[TrackRecord] | None = None) -> AppState:
    ordered = [_track("/music/a.flac"), _track("/music/b.flac")] if tracks is None else tracks
    return AppState(
        scanned_records=ordered,
        last_recommendation=_recommendation(ordered) if ordered else None,
        last_dj_readiness_report=_readiness(),
    )


class _Label:
    """Minimal QLabel double: the narrator status line."""

    def __init__(self) -> None:
        self.texts: list[str] = []

    def setText(self, text: str) -> None:  # noqa: N802 - Qt-compatible test double
        self.texts.append(text)

    @property
    def text(self) -> str:
        return self.texts[-1] if self.texts else ""


class _ReviewScreen:
    """Review-screen double exposing only the narrator surface the controller owns."""

    def __init__(self) -> None:
        self.ai_narrate_status = _Label()
        self.renders: list[AppState] = []

    def render(self, _vm: Any, state: AppState) -> None:
        self.renders.append(state)


class _StateHost:
    """MainWindow double: the controller reaches AppState through it, like the copilot."""

    def __init__(self, state: AppState | None = None) -> None:
        self._state = _ready_state() if state is None else state

    def tr(self, text: str) -> str:
        return text

    def _replace_app_state(self, updated: AppState) -> None:
        self._state = updated


class _Harness:
    """Wire the controller with captured seams instead of a live worker thread."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *,
        state: AppState | None = None,
        narrator: Any = None,
        capture_worker: bool = True,
    ) -> None:
        self.main_thread = threading.current_thread()
        self.host = _StateHost(state)
        self.screen = _ReviewScreen()
        self.narrator_calls: list[tuple[Any, Any, float]] = []
        self.state_changes: list[threading.Thread] = []
        self.jobs: list[tuple[Any, int]] = []

        def default_narrator(recommendation: Any, readiness: Any, *, timeout: float) -> str:
            self.narrator_calls.append((recommendation, readiness, timeout))
            return NARRATIVE

        chosen_narrator: Any = narrator if narrator is not None else default_narrator
        self.controller = AiNarratorController(
            review_screen=self.screen,
            review_vm=object(),
            state=self.host,
            on_state_changed=self._on_state_changed,
            narrator=chosen_narrator,
        )
        if capture_worker:
            monkeypatch.setattr(AiNarratorController, "_start_worker", self._capture_worker)

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


def test_narrate_marks_the_request_busy_then_stores_the_narrative(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _Harness(monkeypatch)
    recommendation = harness.host._state.last_recommendation
    readiness = harness.host._state.last_dj_readiness_report

    harness.controller.narrate()

    assert harness.host._state.is_narrating is True
    assert harness.host._state.ai_narrative_text is None
    assert harness.screen.renders[-1].is_narrating is True
    assert harness.state_changes
    assert harness.jobs and len(harness.jobs) == 1
    # The blocking network call is handed to the worker, never run in the slot.
    assert harness.narrator_calls == []

    harness.run()

    assert harness.narrator_calls == [(recommendation, readiness, AI_NARRATOR_TIMEOUT_SECONDS)]
    assert harness.host._state.is_narrating is False
    assert harness.host._state.ai_narrative_text == NARRATIVE
    assert harness.screen.renders[-1].ai_narrative_text == NARRATIVE
    assert "Set narrative ready" in harness.screen.ai_narrate_status.text
    assert harness.state_changes[-1] is harness.main_thread


def test_narrate_is_ignored_while_a_narrative_is_already_in_flight(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _Harness(monkeypatch)

    harness.controller.narrate()
    harness.controller.narrate()

    assert len(harness.jobs) == 1
    assert len(harness.screen.renders) == 1


def test_narrate_without_a_recommendation_reports_guidance_and_never_calls_the_narrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _Harness(monkeypatch, state=AppState())

    harness.controller.narrate()

    assert harness.jobs == []
    assert harness.narrator_calls == []
    assert harness.host._state.is_narrating is False
    assert "apply a Prep Copilot variant" in harness.screen.ai_narrate_status.text


def test_narrate_without_ordered_tracks_never_calls_the_narrator(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = PlaylistRecommendation(
        ordered_tracks=[],
        transition_scores=[],
        strategy=PlaylistStrategy(
            name="harmonic_journey",
            display_name="Harmonic Journey",
            description="Test strategy",
            weights=ScoringWeights(),
        ),
        warnings=[],
        applied_controls={},
        optimizer="test-optimizer",
        total_score=0.0,
    )
    harness = _Harness(
        monkeypatch,
        state=AppState(last_recommendation=empty, last_dj_readiness_report=_readiness()),
    )

    harness.controller.narrate()

    assert harness.jobs == []
    assert harness.narrator_calls == []
    assert harness.host._state.is_narrating is False


def test_narrate_without_a_readiness_report_never_calls_the_narrator(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _Harness(
        monkeypatch,
        state=AppState(last_recommendation=_recommendation([_track("/music/a.flac")])),
    )

    harness.controller.narrate()

    assert harness.jobs == []
    assert harness.narrator_calls == []
    assert "apply a Prep Copilot variant" in harness.screen.ai_narrate_status.text


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (NanConfigError("API key file not found: /keys/apiIA.env"), "is not configured"),
        (ValueError("the model refused"), "could not explain"),
        (RuntimeError("connection reset"), "failed: connection reset"),
    ],
    ids=["nan-config", "value-error", "unexpected"],
)
def test_narrator_failures_clear_the_busy_flag_and_report_on_the_status_line(
    monkeypatch: pytest.MonkeyPatch, error: Exception, expected: str
) -> None:
    """Every failure shape lands on the status line: no modal, no stuck button."""

    def failing(*_args: Any, **_kwargs: Any) -> str:
        raise error

    harness = _Harness(monkeypatch, narrator=failing)

    harness.controller.narrate()
    harness.run()

    assert harness.host._state.is_narrating is False
    assert harness.host._state.ai_narrative_text is None
    assert expected in harness.screen.ai_narrate_status.text
    assert harness.screen.renders[-1].is_narrating is False


def test_nan_config_failure_points_at_ai_settings_and_the_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guidance, not just diagnosis: where to enable AI, that it applies on restart, and the key file."""

    def failing(*_args: Any, **_kwargs: Any) -> str:
        raise NanConfigError("API key file not found: /keys/apiIA.env")

    harness = _Harness(monkeypatch, narrator=failing)

    harness.controller.narrate()
    harness.run()

    text = harness.screen.ai_narrate_status.text
    assert "Settings" in text
    assert "restart" in text
    assert "API key file" in text


def test_late_worker_results_do_not_override_a_newer_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """A superseded request must not clear the busy flag or overwrite the newer narrative."""
    harness = _Harness(monkeypatch)

    harness.controller.narrate()
    harness.run()
    assert harness.host._state.ai_narrative_text == NARRATIVE

    harness.controller.narrate()
    assert harness.host._state.is_narrating is True

    harness.controller._on_worker_finished("a stale narrative", 1)
    harness.controller._on_worker_failed(RuntimeError("late failure"), 1)

    assert harness.host._state.is_narrating is True
    assert harness.host._state.ai_narrative_text is None

    harness.run(1)
    assert harness.host._state.is_narrating is False


# ---------------------------------------------------------------------------
# Threading and seams
# ---------------------------------------------------------------------------


def test_narrate_runs_the_blocking_narrator_off_the_ui_thread(monkeypatch: pytest.MonkeyPatch, qapp: Any) -> None:
    """narrate_set is a blocking network call, so it must not run in the slot."""
    worker_threads: list[threading.Thread] = []
    release = threading.Event()

    def slow_narrator(_recommendation: Any, _readiness: Any, *, timeout: float) -> str:
        worker_threads.append(threading.current_thread())
        release.wait(5)
        return NARRATIVE

    harness = _Harness(monkeypatch, narrator=slow_narrator, capture_worker=False)
    try:
        harness.controller.narrate()
        assert harness.host._state.is_narrating is True
        assert harness.screen.renders[-1].is_narrating is True

        deadline = time.monotonic() + 5
        while not worker_threads and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)
        assert worker_threads, "the worker never picked up the request"
        assert worker_threads[0] is not harness.main_thread

        release.set()
        while harness.host._state.ai_narrative_text is None and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.01)

        assert harness.host._state.ai_narrative_text == NARRATIVE
        assert harness.host._state.is_narrating is False
        assert harness.state_changes[-1] is harness.main_thread
    finally:
        release.set()
        harness.controller.cancel()


def test_controller_defaults_bind_the_real_set_narrator() -> None:
    controller = AiNarratorController(
        review_screen=_ReviewScreen(),
        review_vm=object(),
        state=_StateHost(),
        on_state_changed=lambda: None,
    )

    assert controller._narrator is narrate_set


def test_state_replacement_supports_a_host_without_its_own_replacer(monkeypatch: pytest.MonkeyPatch) -> None:
    """The controller works with either host shape, like the AI copilot controller does."""
    harness = _Harness(monkeypatch)
    bare_host = SimpleNamespace(_state=harness.host._state, tr=lambda text: text)
    harness.controller._state = bare_host

    harness.controller.narrate()

    assert bare_host._state.is_narrating is True


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

    harness.controller._narrate_thread = cast(Any, _Thread())
    harness.controller.cancel()

    assert interrupted == [True]
    assert waits == [500]


def test_a_superseded_thread_does_not_clear_the_current_worker_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old thread finishes after the DJ asked again; its cleanup must not win."""
    harness = _Harness(monkeypatch)
    current_thread = QThread()
    stale_thread = QThread()
    harness.controller._narrate_thread = current_thread
    harness.controller._narrate_worker = cast(Any, object())
    monkeypatch.setattr(harness.controller, "sender", lambda: stale_thread, raising=False)

    harness.controller._on_worker_cleared()

    assert harness.controller._narrate_thread is current_thread
    assert harness.controller._narrate_worker is not None

    monkeypatch.setattr(harness.controller, "sender", lambda: current_thread, raising=False)
    harness.controller._on_worker_cleared()

    assert harness.controller._narrate_thread is None
    assert harness.controller._narrate_worker is None


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


def test_ai_narrative_transitions_track_the_in_flight_request() -> None:
    state = AppState(ai_narrative_text="an old narrative")

    started = apply_ai_narrative_started(state)

    assert started is not state
    assert started.is_narrating is True
    assert started.ai_narrative_text is None, "a new request must not leave the old narrative on screen"
    assert state.is_narrating is False
    assert state.ai_narrative_text == "an old narrative"

    finished = apply_ai_narrative_finished(started, NARRATIVE)

    assert finished.is_narrating is False
    assert finished.ai_narrative_text == NARRATIVE
    assert started.ai_narrative_text is None

    cleared = apply_ai_narrative_cleared(finished)

    assert cleared.is_narrating is False
    assert cleared.ai_narrative_text is None


def test_storing_a_new_recommendation_clears_the_previous_narrative() -> None:
    """The narrative describes one specific set, so a new recommendation invalidates it."""
    tracks = [_track("/music/a.flac")]
    payload = SimpleNamespace(
        recommendation=_recommendation(tracks),
        explanation=object(),
        quality_report=object(),
        readiness_report=_readiness(),
        variant_name="balanced",
    )
    state = AppState(ai_narrative_text=NARRATIVE, is_narrating=False)

    applied = apply_prep_copilot_variant(state, payload)

    assert applied.ai_narrative_text is None

    completed = apply_recommendation_completion(
        AppState(ai_narrative_text=NARRATIVE),
        SimpleNamespace(
            recommendation=_recommendation(tracks),
            explanation=object(),
            quality_report=object(),
        ),
    )

    assert completed.ai_narrative_text is None
