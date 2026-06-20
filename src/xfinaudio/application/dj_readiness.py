"""Application use cases for DJ readiness reporting."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.exporting.serato_crate import SeratoExportPlan
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.dj_readiness import build_dj_readiness_report as _build_dj_readiness_report
from xfinaudio.quality.dj_readiness import format_dj_readiness_summary as _format_dj_readiness_summary
from xfinaudio.quality.dj_readiness import write_dj_readiness_report as _write_dj_readiness_report
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


def build_application_dj_readiness_report(
    recommendation: PlaylistRecommendation,
    quality_report: RecommendationQualityReport,
    *,
    serato_plan: SeratoExportPlan | None = None,
    serato_volume_root: Path | None = None,
) -> DjReadinessReport:
    """Build the DJ readiness report through the application boundary."""
    return _build_dj_readiness_report(
        recommendation,
        quality_report,
        serato_plan=serato_plan,
        serato_volume_root=serato_volume_root,
    )


def write_application_dj_readiness_report(
    report: DjReadinessReport,
    json_path: Path,
    csv_path: Path,
) -> tuple[Path, Path]:
    """Write DJ readiness report files through the application boundary."""
    return _write_dj_readiness_report(report, json_path, csv_path)


def format_application_dj_readiness_summary(report: DjReadinessReport) -> str:
    """Return DJ readiness summary text through the application boundary."""
    return _format_dj_readiness_summary(report)


__all__ = [
    "build_application_dj_readiness_report",
    "format_application_dj_readiness_summary",
    "write_application_dj_readiness_report",
]
