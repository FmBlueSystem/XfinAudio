"""AI set narrator controller: the recommended set -> a short natural-language arc.

The narrator is a writer, not a source of truth: ``narrate_set`` receives the
current recommendation and DJ readiness report and returns prose built only from
those engine facts. The controller owns the worker lifecycle and the Review
screen's narrative state, so the blocking request never runs on the UI thread and
the busy/result rendering stays render-driven.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.ai import NanConfigError, narrate_set
from xfinaudio.desktop._workers import BackgroundWorker, WorkerRegistry
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.app_state_transitions import (
    apply_ai_narrative_finished,
    apply_ai_narrative_started,
)
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

#: Narration is a reasoning call over a whole set, not a classification one. The
#: adapter's 30s default timed out on the slower Nan models during the Fase 0
#: demo, so this surface allows two full minutes instead of exposing a timeout
#: control.
AI_NARRATOR_TIMEOUT_SECONDS = 120.0

#: Shown while a request is in flight. Long, because a whole-set narration is a
#: heavier call than the copilot's intent extraction.
NARRATING_STATUS = "Narrating the set... this can take up to two minutes"


@dataclass(frozen=True)
class _NarrativeDelivery:
    request_id: int
    value: object


class SetNarrator(Protocol):
    """Seam that turns a recommendation plus its readiness report into prose."""

    def __call__(
        self, recommendation: PlaylistRecommendation, readiness: DjReadinessReport, *, timeout: float
    ) -> str: ...


class AiNarratorController(QObject):
    """Own the "Explícame este set" worker lifecycle and the narrative state.

    A ``QObject`` for the same reason the AI copilot controller is one: the
    blocking narration runs in a ``QThread``, and the completion has to be
    delivered back on the UI thread before anything touches state or widgets.
    """

    narrative_completed = Signal(object)
    narrative_failed = Signal(object)

    def __init__(
        self,
        *,
        review_screen: Any,
        review_vm: Any,
        state: Any,
        on_state_changed: Callable[[], None],
        narrator: SetNarrator = narrate_set,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._worker_registry = WorkerRegistry(self)
        self._review_screen = review_screen
        self._review_vm = review_vm
        # ``state`` is the window, like AiCopilotController: the AppState lives on
        # it (and is read back through ``_app_state``) so every collaborator sees
        # the same replacement.
        self._state = state
        self._on_state_changed = on_state_changed
        self._narrator = narrator
        self._narrate_thread: QThread | None = None
        self._narrate_worker: BackgroundWorker | None = None
        self._current_request_id: int = 0
        self._context: tuple[PlaylistRecommendation, DjReadinessReport] | None = None
        # Re-emitted onto the controller's own thread: the worker's signals reach a
        # plain lambda, so the state and widget work must be marshalled here.
        self.narrative_completed.connect(self.on_completed)
        self.narrative_failed.connect(self.on_failed)

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

    def _set_status(self, text: str) -> None:
        self._review_screen.ai_narrate_status.setText(text)

    # ------------------------------------------------------------------
    # Request entry point
    # ------------------------------------------------------------------

    def narrate(self) -> None:
        """Narrate the current recommendation without blocking the UI thread."""
        self.invalidate_if_context_changed()
        if self._app_state().is_narrating:
            # One request at a time: a second one would race the first for the panel.
            return
        recommendation = self._app_state().last_recommendation
        readiness = self._app_state().last_dj_readiness_report
        if recommendation is None or not recommendation.ordered_tracks or readiness is None:
            # Both facts come from an applied variant, so there is nothing honest to
            # narrate yet -- say which step is missing instead of asking the model.
            # ``self.tr`` is called with a literal on purpose: that is the shape
            # ``lupdate`` extracts, and ``QObject.tr`` resolves the context to this
            # class, so the string reaches the .ts files (the AI copilot controller
            # delegates to the window's ``tr``, which the scanner cannot see).
            self._set_status(self.tr("Generate and apply a Prep Copilot variant before asking for a set narrative."))
            return
        self._current_request_id += 1
        request_id = self._current_request_id
        self._context = (recommendation, readiness)
        self._begin_narrating_state()
        self._start_worker(lambda: self._narrate(recommendation, readiness), request_id)

    def _begin_narrating_state(self) -> None:
        """Mark the request in flight so render() disables the narrate button."""
        self._replace_state(apply_ai_narrative_started(self._app_state()))
        self._review_screen.render(self._review_vm, self._app_state())
        self._on_state_changed()

    def _narrate(self, recommendation: PlaylistRecommendation, readiness: DjReadinessReport) -> str:
        """Worker-thread body: the blocking narration call, off the UI thread."""
        return self._narrator(recommendation, readiness, timeout=AI_NARRATOR_TIMEOUT_SECONDS)

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Release the UI immediately; a blocking transport may finish later."""
        self._current_request_id += 1
        if self._narrate_thread is not None and self._narrate_thread.isRunning():
            self._narrate_thread.requestInterruption()
        self._context = None
        if self._app_state().is_narrating:
            self._replace_state(apply_ai_narrative_finished(self._app_state(), None))
            self._review_screen.render(self._review_vm, self._app_state())
            self._on_state_changed()
            self._set_status(self.tr("Narration cancelled. You can retry."))

    def invalidate_if_context_changed(self) -> None:
        """Invalidate results even when a replacement set retained the busy flag."""
        if self._context is None:
            return
        state = self._app_state()
        recommendation, readiness = self._context
        if state.last_recommendation is recommendation and state.last_dj_readiness_report is readiness:
            return
        self.cancel()
        if self._app_state().ai_narrative_text is not None:
            self._replace_state(apply_ai_narrative_finished(self._app_state(), None))
            self._review_screen.render(self._review_vm, self._app_state())
            self._on_state_changed()
        self._set_status(self.tr("Set changed. Request a new narrative for this set."))

    def _accept_delivery(self, delivery: object) -> bool:
        self.invalidate_if_context_changed()
        return (
            isinstance(delivery, _NarrativeDelivery)
            and delivery.request_id == self._current_request_id
            and self._context is not None
            and self._app_state().is_narrating
        )

    def _start_worker(self, operation: Callable[[], str], request_id: int) -> None:
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
        self._narrate_thread = thread
        self._narrate_worker = worker
        thread.start()

    def _on_worker_finished(self, result: object, request_id: int | None = None) -> None:
        self.narrative_completed.emit(
            _NarrativeDelivery(self._current_request_id if request_id is None else request_id, result)
        )

    def _on_worker_failed(self, error: object, request_id: int | None = None) -> None:
        self.narrative_failed.emit(
            _NarrativeDelivery(self._current_request_id if request_id is None else request_id, error)
        )

    def _on_worker_cleared(self) -> None:
        sender_thread = self.sender()
        if sender_thread is not None and sender_thread is not self._narrate_thread:
            return
        self._narrate_thread = None
        self._narrate_worker = None

    # ------------------------------------------------------------------
    # Terminal handlers
    # ------------------------------------------------------------------

    @Slot(object)
    def on_completed(self, result: object) -> None:
        """Store the narration and render it on the Review screen."""
        if not self._accept_delivery(result):
            return
        narrative = cast(str, cast(_NarrativeDelivery, result).value)
        updated_state = apply_ai_narrative_finished(self._app_state(), narrative)
        self._replace_state(updated_state)
        self._review_screen.render(self._review_vm, updated_state)
        self._on_state_changed()
        self._set_status(self.tr("Set narrative ready"))

    @Slot(object)
    def on_failed(self, error: object) -> None:
        """Report a failed narration on the status line -- never a modal."""
        if not self._accept_delivery(error):
            return
        error = cast(_NarrativeDelivery, error).value
        updated_state = apply_ai_narrative_finished(self._app_state(), None)
        self._replace_state(updated_state)
        self._review_screen.render(self._review_vm, updated_state)
        self._on_state_changed()
        self._set_status(self._failure_message(error))

    def _failure_message(self, error: object) -> str:
        if isinstance(error, NanConfigError):
            return self.tr(
                "AI set narrative is not configured: {0} Use Configure AI to open Settings, "
                "enable AI and check the API key file, then retry."
            ).format(error)
        if isinstance(error, ValueError):
            return self.tr("AI set narrative could not explain the set: {0}").format(error)
        return self.tr("AI set narrative failed: {0}").format(error)


__all__ = ["AI_NARRATOR_TIMEOUT_SECONDS", "NARRATING_STATUS", "AiNarratorController", "SetNarrator"]
