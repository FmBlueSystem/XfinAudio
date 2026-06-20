"""Recommendation quality validation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xfinaudio.quality.dj_readiness import (
        DjReadinessCheck,
        DjReadinessReport,
        ReadinessStatus,
        build_dj_readiness_report,
        export_dj_readiness_csv,
        export_dj_readiness_json,
        format_dj_readiness_summary,
        validate_serato_round_trip,
        write_dj_readiness_report,
    )
    from xfinaudio.quality.recommendation_quality import RecommendationQualityReport, build_quality_report

_EXPORTS: dict[str, tuple[str, str]] = {
    "DjReadinessCheck": ("xfinaudio.quality.dj_readiness", "DjReadinessCheck"),
    "DjReadinessReport": ("xfinaudio.quality.dj_readiness", "DjReadinessReport"),
    "ReadinessStatus": ("xfinaudio.quality.dj_readiness", "ReadinessStatus"),
    "RecommendationQualityReport": ("xfinaudio.quality.recommendation_quality", "RecommendationQualityReport"),
    "build_dj_readiness_report": ("xfinaudio.quality.dj_readiness", "build_dj_readiness_report"),
    "export_dj_readiness_csv": ("xfinaudio.quality.dj_readiness", "export_dj_readiness_csv"),
    "export_dj_readiness_json": ("xfinaudio.quality.dj_readiness", "export_dj_readiness_json"),
    "build_quality_report": ("xfinaudio.quality.recommendation_quality", "build_quality_report"),
    "format_dj_readiness_summary": ("xfinaudio.quality.dj_readiness", "format_dj_readiness_summary"),
    "validate_serato_round_trip": ("xfinaudio.quality.dj_readiness", "validate_serato_round_trip"),
    "write_dj_readiness_report": ("xfinaudio.quality.dj_readiness", "write_dj_readiness_report"),
}

__all__ = [
    "DjReadinessCheck",
    "DjReadinessReport",
    "ReadinessStatus",
    "RecommendationQualityReport",
    "build_dj_readiness_report",
    "export_dj_readiness_csv",
    "export_dj_readiness_json",
    "build_quality_report",
    "format_dj_readiness_summary",
    "validate_serato_round_trip",
    "write_dj_readiness_report",
]


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily to keep pure quality imports isolated."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
