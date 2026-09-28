"""DJ readiness display controller."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication

from xfinaudio.application.dj_readiness import (
    build_application_dj_readiness_report,
    format_application_dj_readiness_summary,
)
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.rendering import _table_item
from xfinaudio.desktop.screens import ReviewScreen
from xfinaudio.desktop.table_populators import populate_dj_readiness_table
from xfinaudio.desktop.theme import _READINESS_STATUS_COLORS, _READINESS_STATUS_LABELS, _READINESS_STATUS_TOOLTIPS
from xfinaudio.quality.dj_readiness import DjReadinessReport
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
        summary = format_application_dj_readiness_summary(report)
        energy_arc = self._energy_arc(recommendation)
        if energy_arc:
            summary = f"{summary} | {energy_arc}"
        self._review_screen.dj_readiness_label.setText(summary)
        self.populate_table(report)

    def _energy_arc(self, recommendation: PlaylistRecommendation) -> str:
        """Return the energy-arc fragment (opener → closer energy), or "" when unavailable.

        Gives the DJ the shape of the set at a glance without opening the JSON
        export; single-track playlists have no arc to describe. The
        recommendation is otherwise an opaque builder input, so anything without
        an ordered_tracks shape simply yields no arc.
        """
        tracks = getattr(recommendation, "ordered_tracks", None)
        energies = [track.energy_level for track in tracks] if tracks else []
        if len(energies) < 2 or energies[0] is None or energies[-1] is None:
            return ""
        return QCoreApplication.translate("DjReadinessController", "Energy arc {0}→{1}").format(
            energies[0], energies[-1]
        )

    def populate_table(self, report: DjReadinessReport) -> None:
        populate_dj_readiness_table(
            self._review_screen.readiness_table,
            report,
            item_factory=_table_item,
            readiness_status_labels=_READINESS_STATUS_LABELS,
            readiness_status_colors=_READINESS_STATUS_COLORS,
            readiness_status_tooltips=_READINESS_STATUS_TOOLTIPS,
        )
