"""Qt recommendation service that owns worker lifecycle and recommendation UI state."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.desktop._workers import BackgroundWorker
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.app_state_transitions import apply_recommendation_completion
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls


def _unwired(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError("RecommendationService dependencies were not wired")


class RecommendationService(QObject):
    """Manage recommendation worker lifecycle and recommendation state-machine."""

    recommendation_completed = Signal(object)
    recommendation_failed = Signal(object)
    worker_cleared = Signal()

    def __init__(self, workflow_service: PlaylistWorkflowService, *, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.workflow_service = workflow_service
        self._recommendation_thread: QThread | None = None
        self._recommendation_worker: BackgroundWorker | None = None
        self._current_request_id: int = 0
        self._scanned_records: Callable[[], list[TrackRecord]] = _unwired
        self._set_is_recommending: Callable[[bool], None] = _unwired
        self._state: AppState | None = None
        self._current_state: Callable[[], AppState] = _unwired
        self._set_state: Callable[[AppState], None] = _unwired
        self._build_screen: Any = None
        self._review_screen: Any = None
        self._export_screen: Any = None
        self._library_screen: Any = None
        self._status_label: Any = None
        self._recommendation_guidance_label: Any = None
        self._tr: Callable[[str], str] = lambda text: text
        self._sync_state: Callable[[], None] = _unwired
        self._clear_recommendation_review: Callable[[], None] = _unwired
        self._show_recommendation: Callable[[list[TrackRecord], str, Any], None] = _unwired
        self._show_transition_review: Callable[[Any], None] = _unwired
        self._selected_track_controls: Callable[[], DJControls | None] = _unwired
        self._desktop_recommendation_records: Callable[..., list[TrackRecord]] = _unwired
        self._set_recommendation_sections_expanded: Callable[[bool], None] = _unwired
        self._set_applied_copilot_variant: Callable[[str | None], None] = _unwired
        self._show_dj_readiness: Callable[..., None] = _unwired
        self._refresh_idle_action_state: Callable[[], None] = _unwired

    def set_state_accessors(
        self,
        *,
        scanned_records: Callable[[], list[TrackRecord]],
        set_is_recommending: Callable[[bool], None],
        state: Callable[[], AppState],
        set_state: Callable[[AppState], None],
    ) -> None:
        self._scanned_records = scanned_records
        self._set_is_recommending = set_is_recommending
        self._current_state = state
        self._state = state()
        self._set_state = set_state

    def set_ui(
        self,
        *,
        build_screen: Any,
        review_screen: Any,
        export_screen: Any,
        library_screen: Any,
        status_label: Any,
        recommendation_guidance_label: Any,
        tr: Callable[[str], str],
    ) -> None:
        self._build_screen = build_screen
        self._review_screen = review_screen
        self._export_screen = export_screen
        self._library_screen = library_screen
        self._status_label = status_label
        self._recommendation_guidance_label = recommendation_guidance_label
        self._tr = tr

    def set_actions(
        self,
        *,
        sync_state: Callable[[], None],
        clear_recommendation_review: Callable[[], None],
        show_recommendation: Callable[[list[TrackRecord], str, Any], None],
        show_transition_review: Callable[[Any], None],
        selected_track_controls: Callable[[], DJControls | None],
        desktop_recommendation_records: Callable[..., list[TrackRecord]],
        set_recommendation_sections_expanded: Callable[[bool], None],
        set_applied_copilot_variant: Callable[[str | None], None],
        show_dj_readiness: Callable[..., None],
        refresh_idle_action_state: Callable[[], None],
    ) -> None:
        self._sync_state = sync_state
        self._clear_recommendation_review = clear_recommendation_review
        self._show_recommendation = show_recommendation
        self._show_transition_review = show_transition_review
        self._selected_track_controls = selected_track_controls
        self._desktop_recommendation_records = desktop_recommendation_records
        self._set_recommendation_sections_expanded = set_recommendation_sections_expanded
        self._set_applied_copilot_variant = set_applied_copilot_variant
        self._show_dj_readiness = show_dj_readiness
        self._refresh_idle_action_state = refresh_idle_action_state

    def start_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: DJControls | None = None,
        spectral_cohesion: float = 0.0,
    ) -> None:
        """Start a background recommendation in a worker thread."""
        if self._recommendation_thread is not None and self._recommendation_thread.isRunning():
            self.cancel()
            self._recommendation_thread.wait(500)
        self._current_request_id += 1
        rid = self._current_request_id
        self._start_recommendation_worker(records, strategy_name, controls, spectral_cohesion, rid)

    def cancel(self) -> None:
        """Request thread interruption if a recommendation is running."""
        if self._recommendation_thread is not None and self._recommendation_thread.isRunning():
            self._recommendation_thread.requestInterruption()
            self._recommendation_thread.wait(500)

    def recommend(self) -> None:
        """Generate and display a playlist recommendation from scanned records."""
        self._require_wired()
        if not self._scanned_records():
            self._clear_recommendation_review()
            self._status_label.setText(self._tr("Scan tracks before recommending"))
            self._recommendation_guidance_label.setText(self._tr("Scan metadata before recommending a playlist."))
            return
        strategy_name = self._build_screen.strategy_combo.currentData()
        controls = self._selected_track_controls()
        if controls is None:
            self._clear_recommendation_review()
            self._review_screen.recommendation_table.setRowCount(0)
            self._set_recommendation_sections_expanded(False)
            self._status_label.setText(self._tr("Select at least one complete track before recommending"))
            return
        records = self._desktop_recommendation_records(controls, strategy_name)
        spectral_cohesion = self._build_screen.spectral_cohesion_value() / 100.0
        self._begin_recommendation_state(len(records))
        self.start_recommendation(records, strategy_name, controls, spectral_cohesion)

    def _begin_recommendation_state(self, candidate_count: int) -> None:
        """Disable recommendation controls while the optimizer runs."""
        self._require_wired()
        self._set_is_recommending(True)
        self._build_screen.recommend_button.setEnabled(False)
        self._library_screen.scan_button.setEnabled(False)
        self._status_label.setText(
            self._tr("Generating recommendation from {0} candidate track(s)").format(candidate_count)
        )
        self._sync_state()

    def _end_recommendation_state(self) -> None:
        """Restore valid idle controls after the optimizer finishes."""
        self._require_wired()
        self._set_is_recommending(False)
        self._refresh_idle_action_state()
        self._sync_state()

    @Slot(object)
    def on_completed(self, result: Any) -> None:
        """Render a completed background recommendation."""
        self._require_wired()
        self._end_recommendation_state()
        updated_state = apply_recommendation_completion(self._current_state(), result)
        self._set_state(updated_state)
        self._state = updated_state
        self._set_applied_copilot_variant(None)
        self._sync_state()
        self._show_recommendation(
            result.recommendation.ordered_tracks,
            result.recommendation.strategy.name,
            result.explanation,
        )
        self._review_screen.review_summary_label.setText(
            self._tr(
                "Review summary: Tracks: {0} | Transitions: {1} | Average transition score: {2:.3f} | Warnings: {3}"
            ).format(
                len(result.recommendation.ordered_tracks),
                len(result.explanation.transitions),
                result.quality_report.average_transition_score,
                result.quality_report.warning_count,
            )
        )
        self._show_dj_readiness(result.recommendation, result.quality_report)
        self._show_transition_review(result.explanation)
        recommended_count = len(result.recommendation.ordered_tracks)
        strategy_name = result.recommendation.strategy.name
        self._status_label.setText(
            self._tr("Recommended {0} track(s) using {1}").format(recommended_count, strategy_name)
        )
        self._export_screen.export_guidance_label.setText(
            self._tr(
                "Inspect the review table before exporting. "
                "Review scores and warnings before any safe export to Serato."
            )
        )

    @Slot(object)
    def on_failed(self, error: object) -> None:
        """Recover the UI if background recommendation generation fails."""
        self._end_recommendation_state()
        self._status_label.setText(self._tr("Recommendation failed: {0}").format(error))

    def on_recommend_requested(self, strategy_name: str, paths: list[str]) -> None:
        """Adapter: BuildScreen emits (strategy_name, paths), recommend reads from widgets."""
        self._require_wired()
        combo_idx = self._build_screen.strategy_combo.findData(strategy_name)
        if combo_idx >= 0:
            self._build_screen.strategy_combo.setCurrentIndex(combo_idx)
        self.recommend()

    def _start_recommendation_worker(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: DJControls | None,
        spectral_cohesion: float,
        request_id: int,
    ) -> None:
        thread = QThread(self)
        worker = BackgroundWorker(
            lambda: self.workflow_service.recommend(
                records, strategy_name, controls=controls, spectral_cohesion=spectral_cohesion
            ),
            request_id=request_id,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result, rid=request_id: self._on_worker_finished(result, rid))
        worker.failed.connect(lambda error, rid=request_id: self._on_worker_failed(error, rid))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_cleared)
        self._recommendation_thread = thread
        self._recommendation_worker = worker
        thread.start()

    def _on_worker_finished(self, result: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return
        self.recommendation_completed.emit(result)

    def _on_worker_failed(self, error: object, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._current_request_id:
            return
        self.recommendation_failed.emit(error)

    def _on_worker_cleared(self) -> None:
        sender_thread = self.sender()
        if sender_thread is not None and sender_thread is not self._recommendation_thread:
            return
        self._recommendation_thread = None
        self._recommendation_worker = None
        self.worker_cleared.emit()

    def _require_wired(self) -> None:
        if any(
            value is None
            for value in (
                self._state,
                self._build_screen,
                self._review_screen,
                self._export_screen,
                self._library_screen,
                self._status_label,
                self._recommendation_guidance_label,
            )
        ):
            raise RuntimeError("RecommendationService dependencies were not wired")


__all__ = ["RecommendationService"]
