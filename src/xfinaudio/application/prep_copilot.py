"""Application use cases for Prep Copilot workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.exporting.explainability import build_playlist_explanation as _build_playlist_explanation
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.quality.recommendation_quality import build_quality_report as _build_quality_report
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class PrepCopilotVariantLike(Protocol):
    """Minimal variant data needed to apply a Prep Copilot selection."""

    name: str
    recommendation: PlaylistRecommendation
    readiness: DjReadinessReport


@dataclass(frozen=True)
class PrepCopilotVariantApplicationResult:
    """Application result for applying a selected Prep Copilot variant."""

    recommendation: PlaylistRecommendation
    explanation: PlaylistExplanation
    quality_report: RecommendationQualityReport
    readiness_report: DjReadinessReport
    variant_name: str


def build_prep_copilot_variant_application(
    variant: PrepCopilotVariantLike,
) -> PrepCopilotVariantApplicationResult:
    """Build the application result for applying a selected Prep Copilot variant."""
    recommendation = variant.recommendation
    return PrepCopilotVariantApplicationResult(
        recommendation=recommendation,
        explanation=_build_playlist_explanation(recommendation),
        quality_report=_build_quality_report(recommendation),
        readiness_report=variant.readiness,
        variant_name=variant.name,
    )


__all__ = [
    "PrepCopilotVariantApplicationResult",
    "PrepCopilotVariantLike",
    "build_prep_copilot_variant_application",
]
