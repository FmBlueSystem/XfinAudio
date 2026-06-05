"""Recommendation quality validation reports."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class RecommendationQualityReport(BaseModel):
    """Metrics for validating recommendation quality against objective signals and manual order."""

    model_config = ConfigDict(frozen=True)

    track_count: int
    transition_count: int
    average_transition_score: float
    bpm_jumps: list[float]
    energy_jumps: list[int]
    warning_count: int
    manual_overlap_ratio: float | None = None
    manual_order_match_prefix_count: int | None = None


def build_quality_report(
    recommendation: PlaylistRecommendation,
    manual_paths: list[str] | tuple[str, ...] | None = None,
) -> RecommendationQualityReport:
    """Build deterministic quality metrics for a playlist recommendation."""
    tracks = recommendation.ordered_tracks
    bpm_jumps = [
        round(abs((right.bpm or 0.0) - (left.bpm or 0.0)), 6) for left, right in zip(tracks, tracks[1:], strict=False)
    ]
    energy_jumps = [
        abs((right.energy_level or 0) - (left.energy_level or 0))
        for left, right in zip(tracks, tracks[1:], strict=False)
    ]
    transition_count = len(recommendation.transition_scores)
    average_transition_score = round(recommendation.total_score / transition_count, 6) if transition_count else 0.0
    manual_overlap_ratio: float | None = None
    manual_order_match_prefix_count: int | None = None
    if manual_paths is not None:
        generated_paths = [track.path for track in tracks]
        manual_overlap_ratio = _overlap_ratio(generated_paths, list(manual_paths))
        manual_order_match_prefix_count = _order_match_prefix_count(generated_paths, list(manual_paths))

    return RecommendationQualityReport(
        track_count=len(tracks),
        transition_count=transition_count,
        average_transition_score=average_transition_score,
        bpm_jumps=bpm_jumps,
        energy_jumps=energy_jumps,
        warning_count=len(recommendation.warnings)
        + sum(len(score.warnings) for score in recommendation.transition_scores),
        manual_overlap_ratio=manual_overlap_ratio,
        manual_order_match_prefix_count=manual_order_match_prefix_count,
    )


def _overlap_ratio(generated_paths: list[str], manual_paths: list[str]) -> float:
    if not manual_paths:
        return 0.0
    return round(len(set(generated_paths) & set(manual_paths)) / len(manual_paths), 6)


def _order_match_prefix_count(generated_paths: list[str], manual_paths: list[str]) -> int:
    count = 0
    for generated_path, manual_path in zip(generated_paths, manual_paths, strict=False):
        if generated_path != manual_path:
            break
        count += 1
    return count


__all__ = ["RecommendationQualityReport", "build_quality_report"]
