"""AI copilot controller: a natural-language set request -> Prep Copilot variants.

The LLM only fills the intent: ``extract_intent`` normalizes the request into a
validated :class:`DJSetIntent`, and the deterministic engine
(``build_prep_copilot_plan``) still owns track selection and ordering. The request
never reads the DJ's strategy/target-count combos -- the intent carries what the DJ
asked for, and the resulting plan is stored through the same
``apply_prep_copilot_plan_generated`` transition the Prep Copilot button uses, so
the existing variants table displays it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.ai import NanConfigError, extract_intent
from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop._workers import BackgroundWorker, WorkerRegistry
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.app_state_transitions import (
    apply_ai_copilot_request_finished,
    apply_ai_copilot_request_started,
    apply_prep_copilot_plan_generated,
)
from xfinaudio.desktop.candidate_routes import (
    ColorAnchorContextRoute,
    RecommendationRecordsRoute,
    resolve_candidate_route,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.loudness_policy import LoudnessBand
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, build_prep_copilot_plan

#: The intent pass is a reasoning call, not a classification one. The adapter's
#: 30s default timed out on the slower Nan models during the Fase 0 demo, so the
#: panel allows a full minute instead of exposing a timeout control.
AI_COPILOT_TIMEOUT_SECONDS = 60.0


class IntentExtractor(Protocol):
    """Seam that turns a DJ request plus the library into a validated intent."""

    def __call__(self, user_request: str, tracks: list[TrackRecord], *, timeout: float) -> DJSetIntent: ...


class PlanGenerationBuilder(Protocol):
    """Seam that turns the AI intent into comparable Prep Copilot variants."""

    def __call__(
        self,
        tracks: list[TrackRecord],
        intent: DJSetIntent,
        *,
        color_anchor_path: str | None = None,
        loudness_band: LoudnessBand,
    ) -> PrepCopilotPlan: ...


class AiCopilotController(QObject):
    """Own the AI copilot worker lifecycle and the panel's request state.

    A ``QObject`` for the same reason the recommendation service is one: the
    blocking extraction runs in a ``QThread``, and the completion has to be
    delivered back on the UI thread before anything touches state or widgets.
    """

    copilot_completed = Signal(object)
    copilot_failed = Signal(object)

    def __init__(
        self,
        *,
        build_screen: Any,
        build_vm: Any,
        state: Any,
        on_state_changed: Callable[[], None],
        desktop_recommendation_records: RecommendationRecordsRoute,
        desktop_color_anchor_candidate_context: ColorAnchorContextRoute,
        intent_extractor: IntentExtractor = extract_intent,
        plan_generation_builder: PlanGenerationBuilder = build_prep_copilot_plan,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._worker_registry = WorkerRegistry(self)
        self._build_screen = build_screen
        self._build_vm = build_vm
        # ``state`` is the window, like PrepCopilotController: the AppState lives on
        # it (and is read back through ``_app_state``) so every collaborator sees the
        # same replacement, including the ones the window re-points on replace.
        self._state = state
        self._on_state_changed = on_state_changed
        # Injected rather than reached for through the state: the candidate routes are
        # collaborators this controller calls, exactly as the recommendation service
        # and PrepCopilotController take them.
        self._desktop_recommendation_records = desktop_recommendation_records
        self._desktop_color_anchor_candidate_context = desktop_color_anchor_candidate_context
        self._intent_extractor = intent_extractor
        self._plan_generation_builder = plan_generation_builder
        self._copilot_thread: QThread | None = None
        self._copilot_worker: BackgroundWorker | None = None
        self._current_request_id: int = 0
        # Re-emitted onto the controller's own thread: the worker's signals reach a
        # plain lambda, so the state and widget work must be marshalled here.
        self.copilot_completed.connect(self.on_completed)
        self.copilot_failed.connect(self.on_failed)

    # ------------------------------------------------------------------
    # State plumbing
    # ------------------------------------------------------------------

    def _app_state(self) -> AppState:
        return self._state._state

    def _replace_state(self, updated_state: AppState) -> None:
        if hasattr(self._state, "_replace_app_state"):
            self._state._replace_app_state(updated_state)
        else:
            self._state._state = updated_state

    def _tr(self, text: str) -> str:
        return str(self._state.tr(text))

    def _set_status(self, text: str) -> None:
        self._build_screen.copilot_ask_status.setText(text)

    # ------------------------------------------------------------------
    # Request entry point
    # ------------------------------------------------------------------

    def ask(self, request: str) -> None:
        """Turn *request* into Prep Copilot variants without blocking the UI thread."""
        if self._app_state().is_asking_copilot:
            # One request at a time: a second one would race the first for the panel.
            return
        text = request.strip()
        if not text:
            self._set_status(self._tr("Describe the set you want before asking the AI copilot."))
            return
        library = list(self._app_state().scanned_records)
        if not library:
            self._set_status(self._tr("Scan your library before asking the AI copilot."))
            return
        controls = self._state._selected_track_controls()
        loudness = getattr(self._state, "settings", AppSettings()).loudness
        loudness_band = LoudnessBand(loudness.target_lufs, loudness.tolerance_lu)
        self._current_request_id += 1
        request_id = self._current_request_id
        self._begin_asking_state(text)
        self._start_worker(lambda: self._generate_plan(text, library, controls, loudness_band), request_id)

    def _begin_asking_state(self, request: str) -> None:
        """Mark the request in flight so render() disables the ask controls."""
        self._replace_state(apply_ai_copilot_request_started(self._app_state(), request))
        self._build_screen.render(self._build_vm, self._app_state())
        self._on_state_changed()

    def _end_asking_state(self) -> None:
        """Clear the in-flight flag so render() re-enables the ask controls."""
        self._replace_state(apply_ai_copilot_request_finished(self._app_state()))
        self._build_screen.render(self._build_vm, self._app_state())
        self._on_state_changed()

    def _generate_plan(
        self,
        request: str,
        library: list[TrackRecord],
        controls: Any,
        loudness_band: LoudnessBand,
    ) -> PrepCopilotPlan:
        """Worker-thread body: extract the intent, then plan the variants.

        Everything that blocks or burns CPU happens here, off the UI thread: the
        request itself is a network call, and the candidate pool is planned from the
        scanned library before the engine places a single track.
        """
        intent = self._intent_extractor(request, library, timeout=AI_COPILOT_TIMEOUT_SECONDS)
        records, color_anchor_path = resolve_candidate_route(
            controls,
            intent.strategy,
            records_route=self._desktop_recommendation_records,
            color_anchor_context_route=self._desktop_color_anchor_candidate_context,
            loudness_band=loudness_band,
        )
        return self._plan_generation_builder(
            records,
            intent,
            color_anchor_path=color_anchor_path,
            loudness_band=loudness_band,
        )

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Request interruption of an in-flight request (window close path)."""
        self._current_request_id += 1
        if self._copilot_thread is not None and self._copilot_thread.isRunning():
            self._copilot_thread.requestInterruption()

    def _start_worker(self, operation: Callable[[], PrepCopilotPlan], request_id: int) -> None:
        thread = QThread(self)
        worker = BackgroundWorker(operation, request_id=request_id)
        self._worker_registry.retain(thread, worker)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result, rid=request_id: self._on_worker_finished(result, rid))
        worker.failed.connect(lambda error, rid=request_id: self._on_worker_failed(error, rid))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_cleared)
        self._copilot_thread = thread
        self._copilot_worker = worker
        thread.start()

    def _on_worker_finished(self, result: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return
        self.copilot_completed.emit(result)

    def _on_worker_failed(self, error: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return
        self.copilot_failed.emit(error)

    def _on_worker_cleared(self) -> None:
        sender_thread = self.sender()
        if sender_thread is not None and sender_thread is not self._copilot_thread:
            return
        self._copilot_thread = None
        self._copilot_worker = None

    # ------------------------------------------------------------------
    # Terminal handlers
    # ------------------------------------------------------------------

    @Slot(object)
    def on_completed(self, result: object) -> None:
        """Store the generated plan and render the variants table."""
        plan = cast(PrepCopilotPlan, result)
        updated_state = apply_prep_copilot_plan_generated(self._app_state(), plan)
        updated_state = apply_ai_copilot_request_finished(updated_state)
        self._replace_state(updated_state)
        self._build_screen.apply_variant_button.setEnabled(True)
        # The table is rebuilt by render() through the same chain the Prep Copilot
        # button uses, so both entry points stay one code path.
        self._build_screen.render(self._build_vm, updated_state)
        self._on_state_changed()
        self._set_status(self._tr("AI copilot generated {0} Prep Copilot variant(s)").format(len(plan.variants)))

    @Slot(object)
    def on_failed(self, error: object) -> None:
        """Report a failed request on the panel's status line -- never a modal."""
        self._end_asking_state()
        self._set_status(self._failure_message(error))

    def _failure_message(self, error: object) -> str:
        if isinstance(error, NanConfigError):
            # The adapter reads its switches from the environment at process start, so
            # a setting toggled on mid-session only applies after a restart: say so
            # instead of sending the DJ back to the same dead end.
            return self._tr(
                "AI copilot is not configured: {0} Enable AI in Settings and restart XfinAudio, "
                "then check that the API key file exists."
            ).format(error)
        if isinstance(error, ValueError):
            return self._tr("AI copilot could not understand the request: {0}").format(error)
        return self._tr("AI copilot failed: {0}").format(error)


__all__ = ["AI_COPILOT_TIMEOUT_SECONDS", "AiCopilotController", "IntentExtractor", "PlanGenerationBuilder"]
