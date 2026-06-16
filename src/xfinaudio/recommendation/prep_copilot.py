"""DJ prep copilot planning helpers.

This module turns a DJ set intent into a small set of comparable playlist
variants. It keeps the human DJ in control: intent and hard gates lead; the
algorithm only proposes auditable options.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
from xfinaudio.recommendation.strategies import StrategyName

if TYPE_CHECKING:
    from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport  # noqa: F401
    from xfinaudio.quality.recommendation_quality import RecommendationQualityReport  # noqa: F401

PrepVariantName = Literal["safe", "balanced", "adventurous"]


class DJSetIntent(BaseModel):
    """Human DJ intent for preparing a focused playlist candidate set."""

    model_config = ConfigDict(frozen=True)

    name: str
    strategy: StrategyName | str = "harmonic_journey"
    target_track_count: int = Field(default=25, ge=2, le=100)
    start_path: str | None = None
    end_path: str | None = None
    required_paths: list[str] = Field(default_factory=list)
    excluded_paths: set[str] = Field(default_factory=set)
    genre_focus: str | None = None


class PrepCopilotVariant(BaseModel):
    """One comparable DJ prep option for the same set intent."""

    model_config = ConfigDict(frozen=True)

    name: PrepVariantName
    description: str
    recommendation: PlaylistRecommendation
    readiness: DjReadinessReport
    warnings: list[str]
    blockers: list[str]


class PrepCopilotPlan(BaseModel):
    """Three-option prep plan generated from one DJ set intent."""

    model_config = ConfigDict(frozen=True)

    intent: DJSetIntent
    variants: list[PrepCopilotVariant]


def build_prep_copilot_plan(tracks: list[TrackRecord], intent: DJSetIntent) -> PrepCopilotPlan:
    """Build safe, balanced, and adventurous playlist variants for one DJ set intent."""
    from xfinaudio.quality.dj_readiness import DjReadinessReport  # noqa: F401

    PrepCopilotVariant.model_rebuild()
    variants = [
        _build_variant("safe", tracks, intent),
        _build_variant("balanced", tracks, intent),
        _build_variant("adventurous", tracks, intent),
    ]
    return PrepCopilotPlan(intent=intent, variants=variants)


def _build_variant(name: PrepVariantName, tracks: list[TrackRecord], intent: DJSetIntent) -> PrepCopilotVariant:
    from xfinaudio.quality.dj_readiness import build_dj_readiness_report
    from xfinaudio.quality.recommendation_quality import build_quality_report

    # Guarantee the forward-ref model is rebuilt at the real construction site, regardless of the
    # import order that first loaded this module.
    _ensure_prep_copilot_variant_model()

    variant_tracks, variant_warnings = _filter_tracks_for_variant(name, tracks, intent)
    controls = DJControls(
        start_path=intent.start_path,
        end_path=intent.end_path,
        manual_order_paths=_manual_order_paths(intent),
        excluded_paths=intent.excluded_paths,
    )
    recommendation = recommend_playlist(variant_tracks, intent.strategy, controls=controls)
    recommendation = _limit_recommendation(recommendation, intent.target_track_count)
    readiness = build_dj_readiness_report(recommendation, build_quality_report(recommendation))
    readiness = _add_required_track_gate(readiness, recommendation, intent)
    blockers = [check.label for check in readiness.checks if check.status == "blocked"]
    warnings = [*variant_warnings, *recommendation.warnings]
    return PrepCopilotVariant(
        name=name,
        description=_variant_description(name),
        recommendation=recommendation,
        readiness=readiness,
        warnings=warnings,
        blockers=blockers,
    )


def _filter_tracks_for_variant(
    name: PrepVariantName, tracks: list[TrackRecord], intent: DJSetIntent
) -> tuple[list[TrackRecord], list[str]]:
    if intent.genre_focus is None:
        return tracks, []
    if name == "safe":
        focused = [
            track for track in tracks if track.path in _protected_paths(intent) or track.genre == intent.genre_focus
        ]
        return focused, []
    if name == "balanced":
        focused = [
            track
            for track in tracks
            if track.path in _protected_paths(intent)
            or track.genre == intent.genre_focus
            or intent.genre_focus in set(track.tags or [])
        ]
        return focused, []
    return tracks, [f"adventurous variant may bridge outside genre focus: {intent.genre_focus}"]


def _manual_order_paths(intent: DJSetIntent) -> list[str]:
    paths: list[str] = []
    if intent.start_path is not None:
        paths.append(intent.start_path)
    paths.extend(path for path in intent.required_paths if path not in paths)
    return paths


def _protected_paths(intent: DJSetIntent) -> set[str]:
    protected = set(intent.required_paths)
    if intent.start_path is not None:
        protected.add(intent.start_path)
    if intent.end_path is not None:
        protected.add(intent.end_path)
    return protected


def _limit_recommendation(recommendation: PlaylistRecommendation, target_track_count: int) -> PlaylistRecommendation:
    if len(recommendation.ordered_tracks) <= target_track_count:
        return recommendation
    ordered_tracks = recommendation.ordered_tracks[:target_track_count]
    transition_scores = recommendation.transition_scores[: max(target_track_count - 1, 0)]
    return recommendation.model_copy(
        update={
            "ordered_tracks": ordered_tracks,
            "transition_scores": transition_scores,
            "total_score": sum(score.total_score for score in transition_scores),
        }
    )


def _add_required_track_gate(
    readiness: DjReadinessReport, recommendation: PlaylistRecommendation, intent: DJSetIntent
) -> DjReadinessReport:
    from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport

    required_paths = set(intent.required_paths)
    if not required_paths:
        return readiness
    recommended_paths = {track.path for track in recommendation.ordered_tracks}
    missing_required_count = len(required_paths - recommended_paths)
    if missing_required_count == 0:
        checks = [
            *readiness.checks,
            DjReadinessCheck(
                label="Required tracks",
                status="ready",
                detail="All required tracks are present in the playlist variant",
            ),
        ]
    else:
        missing_check = DjReadinessCheck(
            label="Required tracks",
            status="blocked",
            detail=f"{missing_required_count} required track(s) could not pass playlist gates",
        )
        if any("BPM jump" in warning for warning in recommendation.warnings):
            bpm_check = DjReadinessCheck(
                label="BPM continuity",
                status="blocked",
                detail="A required track was dropped because it would exceed the adjacent BPM gate",
            )
            checks = [*readiness.checks, bpm_check, missing_check]
        else:
            checks = [*readiness.checks, missing_check]
    blocker_count = sum(1 for item in checks if item.status == "blocked")
    review_count = sum(1 for item in checks if item.status == "needs_review")
    status = "blocked" if blocker_count else "needs_review" if review_count else "ready"
    summary = readiness.summary
    if status == "blocked" and readiness.status != "blocked":
        summary = f"Blocked — {blocker_count} blocker(s), {review_count} review item(s); required tracks missing"
    return DjReadinessReport(
        status=status,
        summary=summary,
        checks=checks,
        blocker_count=blocker_count,
        review_count=review_count,
    )


def _variant_description(name: PrepVariantName) -> str:
    return {
        "safe": "Strictest option: stays close to the requested genre focus and hard gates.",
        "balanced": "Middle option: allows tagged bridges while preserving the set intent.",
        "adventurous": "Exploratory option: allows broader bridges but keeps readiness checks visible.",
    }[name]


__all__ = [
    "DJSetIntent",
    "PrepCopilotPlan",
    "PrepCopilotVariant",
    "PrepVariantName",
    "build_prep_copilot_plan",
]


def _ensure_prep_copilot_variant_model() -> None:
    """Resolve the forward reference for PrepCopilotVariant.readiness.

    Called eagerly at import time AND lazily before construction. The eager call tolerates the
    import-order cycle: if ``quality.dj_readiness`` is still being initialized (which happens when
    the ``quality`` package is imported before ``recommendation``), the rebuild is skipped and
    completed later by the lazy call at the construction site.
    """
    if PrepCopilotVariant.__pydantic_complete__:
        return
    try:
        from xfinaudio.quality.dj_readiness import DjReadinessReport  # noqa: F401
    except ImportError:
        # quality.dj_readiness is mid-initialization; defer the rebuild to a later call once both
        # packages are fully loaded (see _build_variant).
        return

    PrepCopilotVariant.model_rebuild()


_ensure_prep_copilot_variant_model()
