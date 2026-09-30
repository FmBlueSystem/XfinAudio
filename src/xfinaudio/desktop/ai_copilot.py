"""Interpret, visibly confirm, then generate Create variants with the local engine.

Provider suggestions never select/order tracks or mutate current recommendations.
The controller snapshots inputs on the UI thread and invalidates stale completions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.ai import NanConfigError, extract_intent
from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop._workers import BackgroundWorker, WorkerRegistry
from xfinaudio.desktop.ai_create_constraints import confirmed_intent
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
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.loudness_policy import LoudnessBand
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, build_prep_copilot_plan

#: The intent pass is a reasoning call, not a classification one. The adapter's
#: 30s default timed out on the slower Nan models during the Fase 0 demo, so the
#: panel allows a full minute instead of exposing a timeout control.
AI_COPILOT_TIMEOUT_SECONDS = 60.0


class IntentExtractor(Protocol):
    """Seam that turns a DJ request plus the library into a validated intent."""

    def __call__(
        self,
        user_request: str,
        tracks: list[TrackRecord],
        *,
        timeout: float,
        include_track_titles: bool = False,
    ) -> DJSetIntent: ...


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
        candidate_routes_factory: Callable[[], tuple[RecommendationRecordsRoute, ColorAnchorContextRoute]]
        | None = None,
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
        self._candidate_routes_factory = candidate_routes_factory
        self._pending_intent: DJSetIntent | None = None
        self._request_context: tuple[Any, ...] | None = None
        self._stage = "interpret"
        if hasattr(build_screen, "copilot_confirm_requested"):
            build_screen.copilot_confirm_requested.connect(self.confirm)
            build_screen.copilot_cancel_requested.connect(self.cancel)
            build_screen.copilot_edit_requested.connect(self.edit)
            build_screen.copilot_ask_input.textEdited.connect(self.edit)
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
        self._clear_preview()
        self._request_context = self._context()
        self._stage = "interpret"
        self._current_request_id += 1
        request_id = self._current_request_id
        share = getattr(self._build_screen, "copilot_share_titles", None)
        include_titles = share is not None and share.isChecked()
        if share is not None:
            share.setChecked(False)
        self._begin_asking_state(text)
        extractor = self._intent_extractor

        def operation() -> DJSetIntent:
            if include_titles:
                return extractor(text, library, timeout=AI_COPILOT_TIMEOUT_SECONDS, include_track_titles=True)
            return extractor(text, library, timeout=AI_COPILOT_TIMEOUT_SECONDS)

        self._start_worker(operation, request_id)

    def _context(self) -> tuple[Any, ...]:
        loudness = getattr(self._state, "settings", AppSettings()).loudness
        return (
            list(self._app_state().scanned_records),
            self._state._selected_track_controls(),
            LoudnessBand(loudness.target_lufs, loudness.tolerance_lu),
            self._build_screen.copilot_ask_input.text() if hasattr(self._build_screen, "copilot_ask_input") else None,
        )

    def _clear_preview(self) -> None:
        self._pending_intent = None
        if hasattr(self._build_screen, "intent_preview"):
            self._build_screen.intent_preview.clear()

    def _set_cancel_enabled(self, enabled: bool) -> None:
        if hasattr(self._build_screen, "copilot_cancel_button"):
            self._build_screen.copilot_cancel_button.setEnabled(enabled)

    def edit(self, *_args: object) -> None:
        self.cancel()
        if hasattr(self._build_screen, "copilot_ask_input"):
            self._build_screen.copilot_ask_input.setFocus()
        self._set_status(self._tr("Edit the request, then ask again to review its interpretation."))

    @Slot(object)
    def confirm(self, intent: object = None) -> None:
        if self._pending_intent is None or self._app_state().is_asking_copilot:
            return
        if self._request_context != self._context():
            self.cancel()
            self._set_status(self._tr("Library or constraints changed. Ask again before generating."))
            return
        if self._app_state().is_preparing_copilot or self._app_state().is_recommending or self._app_state().is_scanning:
            self._set_status(self._tr("Wait for the current scan or generation to finish, then confirm."))
            return
        assert self._request_context is not None
        library, controls, band = self._request_context[:3]
        try:
            chosen = confirmed_intent(
                intent if isinstance(intent, DJSetIntent) else self._pending_intent, controls, library
            )
        except ValueError as error:
            self._set_status(self._failure_message(error))
            return
        routes = (
            self._candidate_routes_factory()
            if self._candidate_routes_factory is not None
            else (self._desktop_recommendation_records, self._desktop_color_anchor_candidate_context)
        )
        controls = DJControls(
            start_path=chosen.start_path,
            end_path=chosen.end_path,
            locked_paths=frozenset(chosen.required_paths),
            excluded_paths=frozenset(chosen.excluded_paths),
            manual_order_paths=list(controls.manual_order_paths) if controls else [],
            genre=chosen.genre_focus,
        )
        self._clear_preview()
        self._stage = "plan"
        self._current_request_id += 1
        self._begin_asking_state(self._app_state().ai_copilot_request or "")
        self._set_status(self._tr("Generating confirmed variants locally..."))
        self._start_worker(lambda: self._generate_plan(chosen, controls, band, routes), self._current_request_id)

    def _begin_asking_state(self, request: str) -> None:
        """Mark the request in flight so render() disables the ask controls."""
        self._set_cancel_enabled(True)
        self._build_screen.copilot_is_planning = self._stage == "plan"
        self._replace_state(apply_ai_copilot_request_started(self._app_state(), request))
        self._build_screen.render(self._build_vm, self._app_state())
        self._on_state_changed()

    def _end_asking_state(self) -> None:
        """Clear the in-flight flag so render() re-enables the ask controls."""
        self._set_cancel_enabled(False)
        self._replace_state(apply_ai_copilot_request_finished(self._app_state()))
        self._build_screen.render(self._build_vm, self._app_state())
        self._on_state_changed()

    def _generate_plan(
        self,
        intent: DJSetIntent,
        controls: Any,
        loudness_band: LoudnessBand,
        routes: tuple[RecommendationRecordsRoute, ColorAnchorContextRoute],
    ) -> PrepCopilotPlan:
        """Plan only after explicit confirmation, using UI-thread snapshots."""
        records, color_anchor_path = resolve_candidate_route(
            controls,
            intent.strategy,
            records_route=routes[0],
            color_anchor_context_route=routes[1],
            loudness_band=loudness_band,
        )
        return self._plan_generation_builder(
            records, intent, color_anchor_path=color_anchor_path, loudness_band=loudness_band
        )

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Request interruption of an in-flight request (window close path)."""
        self._current_request_id += 1
        self._clear_preview()
        self._set_cancel_enabled(False)
        if self._app_state().is_asking_copilot:
            self._end_asking_state()
        self._set_status(self._tr("AI request canceled. Previous results are unchanged."))
        if self._copilot_thread is not None and self._copilot_thread.isRunning():
            self._copilot_thread.requestInterruption()

    def _start_worker(self, operation: Callable[[], object], request_id: int) -> None:
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
        self.copilot_completed.emit((self._current_request_id if request_id is None else request_id, result))

    def _on_worker_failed(self, error: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return
        self.copilot_failed.emit((self._current_request_id if request_id is None else request_id, error))

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
        request_id, payload = cast(tuple[int, object], result)
        if request_id != self._current_request_id:
            return
        if self._request_context != self._context():
            self.cancel()
            self._set_status(self._tr("Library or constraints changed. Ask again before generating."))
            return
        if self._stage == "interpret":
            assert self._request_context is not None
            library, controls, band = self._request_context[:3]
            try:
                self._pending_intent = confirmed_intent(cast(DJSetIntent, payload), controls, library)
            except ValueError as error:
                self.on_failed((request_id, error))
                return
            self._end_asking_state()
            self._set_cancel_enabled(True)
            if hasattr(self._build_screen, "intent_preview"):
                labels = {track.path: track.title or "Untitled track" for track in library}
                chosen = self._pending_intent
                summary = self._tr("{0} locked · {1} excluded · loudness {2:g} ± {3:g} LU").format(
                    len(chosen.required_paths), len(chosen.excluded_paths), band.target_lufs, band.tolerance_lu
                )
                for label, path in (("Start", chosen.start_path), ("End", chosen.end_path)):
                    if path:
                        summary += f" · {label}: {labels.get(path, 'Unknown track')}"
                self._build_screen.intent_preview.show_intent(chosen, summary)
                self._build_screen.controls_scroll.ensureWidgetVisible(self._build_screen.intent_preview)
            self._set_status(self._tr("Review the interpretation, then confirm to generate locally."))
            return
        plan = cast(PrepCopilotPlan, payload)
        self._set_cancel_enabled(False)
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
        request_id, payload = cast(tuple[int, object], error)
        if request_id != self._current_request_id:
            return
        self._end_asking_state()
        self._set_status(self._failure_message(payload))

    def _failure_message(self, error: object) -> str:
        if isinstance(error, NanConfigError):
            return self._tr(
                "AI copilot is not configured. Choose Configure AI to enable it in Settings "
                "and check the API key file, then retry."
            )
        if isinstance(error, ValueError):
            return self._tr("AI copilot could not understand the request: {0}").format(error)
        return self._tr("AI copilot failed: {0}").format(error)


__all__ = ["AI_COPILOT_TIMEOUT_SECONDS", "AiCopilotController", "IntentExtractor", "PlanGenerationBuilder"]
