"""Application use cases for Prep Copilot workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.exporting.explainability import build_playlist_explanation as _build_playlist_explanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.quality.recommendation_quality import build_quality_report as _build_quality_report
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, build_prep_copilot_plan

PlanBuilder = Callable[[list[TrackRecord], DJSetIntent], PrepCopilotPlan]


@dataclass(frozen=True)
class PrepCopilotGenerationRequest:
    """Application request for generating Prep Copilot variants from UI-derived inputs."""

    strategy: str
    target_track_count: int
    start_path: str | None = None
    required_paths: list[str] = field(default_factory=list)
    genre_focus: str | None = None


def generate_prep_copilot_plan(
    records: list[TrackRecord],
    request: PrepCopilotGenerationRequest,
    *,
    plan_builder: PlanBuilder = build_prep_copilot_plan,
) -> PrepCopilotPlan:
    """Generate a Prep Copilot plan from UI-derived generation parameters."""
    intent = DJSetIntent(
        name="Desktop Prep Copilot",
        strategy=request.strategy,
        target_track_count=request.target_track_count,
        start_path=request.start_path,
        required_paths=request.required_paths,
        genre_focus=request.genre_focus,
    )
    return plan_builder(records, intent)


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
    "generate_prep_copilot_plan",
    "PrepCopilotGenerationRequest",
    "PrepCopilotVariantApplicationResult",
    "PrepCopilotVariantLike",
    "build_prep_copilot_variant_application",
]
