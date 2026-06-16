"""Recommendation coordination logic extracted from MainWindow.

``RecommendationCoordinator`` owns the recommendation state-machine and
signal-handler logic. It reads state and widgets through a ``host`` handle
(the ``MainWindow``) via the ``RecommendationHost`` Protocol.
"""

from __future__ import annotations

from typing import Any, Protocol

from PySide6.QtCore import Slot

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls


class RecommendationHost(Protocol):
    """Structural host boundary for ``RecommendationCoordinator``.

    Declares only the ``MainWindow`` members the coordinator reads or mutates,
    decoupling recommendation orchestration from the concrete window type.
    """

    scanned_records: list[TrackRecord]
    workflow_service: Any
    _is_recommending: bool
    _state: Any
    _recommendation_controller: Any
    _build_screen: Any
    _review_screen: Any
    _export_screen: Any
    _library_screen: Any
    status_label: Any
    recommendation_guidance_label: Any
    last_recommendation: Any
    last_playlist_explanation: Any
    last_quality_report: Any

    def tr(self, text: str) -> str: ...
    def _sync_state(self) -> None: ...
    def clear_recommendation_review(self) -> None: ...
    def show_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        explanation: Any = None,
    ) -> None: ...
    def show_transition_review(self, explanation: Any) -> None: ...
    def _selected_track_controls(self) -> DJControls | None: ...
    def _desktop_recommendation_records(
        self, controls: DJControls | None, strategy_name: str | None = None
    ) -> list[TrackRecord]: ...
    def _set_recommendation_sections_expanded(self, expanded: bool) -> None: ...
    def _set_applied_copilot_variant(self, variant_name: str | None) -> None: ...
    def _show_dj_readiness(
        self,
        recommendation: Any,
        quality_report: Any,
        *,
        serato_plan: Any = None,
        serato_volume_root: Any = None,
    ) -> None: ...
    def _refresh_idle_action_state(self) -> None: ...


class RecommendationCoordinator:
    """Qt-aware recommendation orchestration extracted from MainWindow.

    State and widget access flow through ``host`` (the ``MainWindow``).
    """

    def __init__(self, host: RecommendationHost) -> None:
        self._host = host

    def recommend(self) -> None:
        """Generate and display a playlist recommendation from scanned records."""
        host = self._host
        if not host.scanned_records:
            host.clear_recommendation_review()
            host.status_label.setText(host.tr("Scan tracks before recommending"))
            host.recommendation_guidance_label.setText(host.tr("Scan metadata before recommending a playlist."))
            return
        strategy_name = host._build_screen.strategy_combo.currentText()
        controls = host._selected_track_controls()
        if controls is None:
            host.clear_recommendation_review()
            host._review_screen.recommendation_table.setRowCount(0)
            host._set_recommendation_sections_expanded(False)
            host.status_label.setText(host.tr("Select at least one complete track before recommending"))
            return
        records = host._desktop_recommendation_records(controls, strategy_name)
        spectral_cohesion = host._build_screen.spectral_cohesion_value() / 100.0
        self._begin_recommendation_state(len(records))
        self._start_recommendation_worker(records, strategy_name, controls, spectral_cohesion)

    def _begin_recommendation_state(self, candidate_count: int) -> None:
        """Disable recommendation controls while the optimizer runs."""
        host = self._host
        host._is_recommending = True
        host._build_screen.recommend_button.setEnabled(False)
        host._library_screen.scan_button.setEnabled(False)
        host.status_label.setText(
            host.tr("Generating recommendation from {0} candidate track(s)").format(candidate_count)
        )
        host._sync_state()

    def _end_recommendation_state(self) -> None:
        """Restore valid idle controls after the optimizer finishes."""
        host = self._host
        host._is_recommending = False
        host._refresh_idle_action_state()
        host._sync_state()

    def _start_recommendation_worker(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: DJControls | None = None,
        spectral_cohesion: float = 0.0,
    ) -> None:
        """Delegate recommendation thread lifecycle to RecommendationController."""
        # Re-sync the controller's workflow_service from the host so a workflow
        # swapped in after construction (e.g. tests, runtime reconfiguration) is used.
        self._host._recommendation_controller.workflow_service = self._host.workflow_service
        self._host._recommendation_controller.start_recommendation(
            records, strategy_name, controls, spectral_cohesion=spectral_cohesion
        )

    @Slot(object)
    def on_completed(self, result: Any) -> None:
        """Render a completed background recommendation."""
        host = self._host
        self._end_recommendation_state()
        host._set_applied_copilot_variant(None)
        host.last_recommendation = result.recommendation
        host.last_playlist_explanation = result.explanation
        host.last_quality_report = result.quality_report
        host._state.playlist_removed_paths = frozenset()
        host._sync_state()
        host.show_recommendation(
            result.recommendation.ordered_tracks,
            result.recommendation.strategy.name,
            result.explanation,
        )
        host._review_screen.review_summary_label.setText(
            host.tr(
                "Review summary: Tracks: {0} | Transitions: {1} | Average transition score: {2:.3f} | Warnings: {3}"
            ).format(
                len(result.recommendation.ordered_tracks),
                len(result.explanation.transitions),
                result.quality_report.average_transition_score,
                result.quality_report.warning_count,
            )
        )
        host._show_dj_readiness(result.recommendation, result.quality_report)
        host.show_transition_review(result.explanation)
        recommended_count = len(result.recommendation.ordered_tracks)
        strategy_name = result.recommendation.strategy.name
        host.status_label.setText(
            host.tr("Recommended {0} track(s) using {1}").format(recommended_count, strategy_name)
        )
        host._export_screen.export_guidance_label.setText(
            host.tr(
                "Inspect the review table before exporting. "
                "Review scores and warnings before any safe export to Serato."
            )
        )

    @Slot(object)
    def on_failed(self, error: object) -> None:
        """Recover the UI if background recommendation generation fails."""
        self._end_recommendation_state()
        self._host.status_label.setText(self._host.tr("Recommendation failed: {0}").format(error))

    def on_recommend_requested(self, strategy_name: str, paths: list[str]) -> None:
        """Adapter: BuildScreen emits (strategy_name, paths), recommend reads from widgets."""
        host = self._host
        combo_idx = host._build_screen.strategy_combo.findText(strategy_name)
        if combo_idx >= 0:
            host._build_screen.strategy_combo.setCurrentIndex(combo_idx)
        self.recommend()
