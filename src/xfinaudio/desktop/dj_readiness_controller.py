"""DJ readiness display controller."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from xfinaudio.application.dj_readiness import build_application_dj_readiness_report
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.rendering import _table_item
from xfinaudio.desktop.screens import ReviewScreen
from xfinaudio.desktop.table_populators import populate_dj_readiness_table
from xfinaudio.desktop.theme import _READINESS_STATUS_COLORS, _READINESS_STATUS_LABELS, _READINESS_STATUS_TOOLTIPS
from xfinaudio.quality.dj_readiness import DjReadinessReport, format_dj_readiness_summary
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

ReadinessBuilder = Callable[..., DjReadinessReport]


class DjReadinessController:
    def __init__(
        self,
        *,
        state: AppState,
        review_screen: ReviewScreen,
        sync_state: Callable[[], None],
        last_report_setter: Callable[[DjReadinessReport | None], None],
        readiness_builder: ReadinessBuilder = build_application_dj_readiness_report,
    ) -> None:
        self._state = state
        self._review_screen = review_screen
        self._sync_state = sync_state
        self._last_report_setter = last_report_setter
        self._readiness_builder = readiness_builder

    def show(
        self,
        recommendation: PlaylistRecommendation,
        quality_report: RecommendationQualityReport,
        *,
        serato_plan: Any | None = None,
        serato_volume_root: Path | None = None,
    ) -> None:
        report = self._readiness_builder(
            recommendation,
            quality_report,
            serato_plan=serato_plan,
            serato_volume_root=serato_volume_root,
        )
        self._last_report_setter(report)
        self._sync_state()
        self._review_screen.dj_readiness_label.setText(format_dj_readiness_summary(report))
        self.populate_table(report)

    def populate_table(self, report: DjReadinessReport) -> None:
        populate_dj_readiness_table(
            self._review_screen.readiness_table,
            report,
            item_factory=_table_item,
            readiness_status_labels=_READINESS_STATUS_LABELS,
            readiness_status_colors=_READINESS_STATUS_COLORS,
            readiness_status_tooltips=_READINESS_STATUS_TOOLTIPS,
        )
