"""DJ readiness checks for playlist and Serato export confidence."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from xfinaudio.exporting.serato_crate import SeratoExportPlan, validate_serato_crate_file
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import MAX_ADJACENT_BPM_DIFFERENCE_PERCENT, PlaylistRecommendation

ReadinessStatus = Literal["ready", "needs_review", "blocked"]
_STATUS_LABELS: dict[ReadinessStatus, str] = {
    "ready": "Ready",
    "needs_review": "Needs Review",
    "blocked": "Blocked",
}
_STATUS_RANK: dict[ReadinessStatus, int] = {"ready": 0, "needs_review": 1, "blocked": 2}


class DjReadinessCheck(BaseModel):
    """One operational readiness signal for a DJ playlist."""

    model_config = ConfigDict(frozen=True)

    label: str
    status: ReadinessStatus
    detail: str


class DjReadinessReport(BaseModel):
    """Aggregated readiness result for taking a playlist into Serato or performance prep."""

    model_config = ConfigDict(frozen=True)

    status: ReadinessStatus
    summary: str
    checks: list[DjReadinessCheck]
    blocker_count: int
    review_count: int


def build_dj_readiness_report(
    recommendation: PlaylistRecommendation,
    quality_report: RecommendationQualityReport,
    *,
    serato_plan: SeratoExportPlan | None = None,
    serato_volume_root: Path | None = None,
    min_average_transition_score: float = 0.65,
) -> DjReadinessReport:
    """Build an operational readiness report from recommendation quality and optional Serato state."""
    checks = [
        _playlist_size_check(recommendation),
        _metadata_check(recommendation),
        _bpm_continuity_check(recommendation),
        _transition_warning_check(recommendation),
        _average_score_check(quality_report, min_average_transition_score),
    ]
    if serato_plan is not None:
        checks.append(validate_serato_round_trip(serato_plan, volume_root=serato_volume_root))

    status = _worst_status(check.status for check in checks)
    blocker_count = sum(1 for check in checks if check.status == "blocked")
    review_count = sum(1 for check in checks if check.status == "needs_review")
    max_bpm_jump = _max_bpm_jump_percent(recommendation)
    summary = (
        f"{_STATUS_LABELS[status]} — "
        f"{blocker_count} blocker(s), {review_count} review item(s); "
        f"max BPM jump {max_bpm_jump:.2f}%"
    )
    return DjReadinessReport(
        status=status,
        summary=summary,
        checks=checks,
        blocker_count=blocker_count,
        review_count=review_count,
    )


def validate_serato_round_trip(plan: SeratoExportPlan, *, volume_root: Path | None = None) -> DjReadinessCheck:
    """Validate that a written Serato crate matches the plan and its track paths resolve on disk."""
    if not plan.target_path.exists():
        return DjReadinessCheck(
            label="Serato round-trip",
            status="blocked",
            detail=f"Serato crate was not written: {plan.target_path}",
        )
    if not validate_serato_crate_file(plan):
        return DjReadinessCheck(
            label="Serato round-trip",
            status="blocked",
            detail="Serato crate bytes do not match the planned export",
        )

    root = volume_root or plan.serato_root.parent
    unresolved = [relative_path for relative_path in plan.relative_paths if not (root / Path(relative_path)).exists()]
    if unresolved:
        track_word = "track" if len(unresolved) == 1 else "tracks"
        return DjReadinessCheck(
            label="Serato round-trip",
            status="blocked",
            detail=f"{len(unresolved)} unresolved {track_word}; Serato may not load those files",
        )

    return DjReadinessCheck(
        label="Serato round-trip",
        status="ready",
        detail=f"Serato crate validates and {len(plan.relative_paths)} track(s) resolve on disk",
    )


def format_dj_readiness_summary(report: DjReadinessReport) -> str:
    """Return a compact desktop label for a readiness report."""
    return f"DJ Readiness: {report.summary}"


def _playlist_size_check(recommendation: PlaylistRecommendation) -> DjReadinessCheck:
    track_count = len(recommendation.ordered_tracks)
    if track_count < 2:
        return DjReadinessCheck(
            label="Playlist size",
            status="blocked",
            detail="At least 2 tracks are required to validate a DJ transition",
        )
    return DjReadinessCheck(
        label="Playlist size",
        status="ready",
        detail=f"{track_count} track(s) available for transition review",
    )


def _metadata_check(recommendation: PlaylistRecommendation) -> DjReadinessCheck:
    incomplete = [track for track in recommendation.ordered_tracks if track.metadata_status != "complete"]
    missing = [track for track in recommendation.ordered_tracks if track.missing_required_fields]
    if incomplete or missing:
        affected_paths = {track.path for track in [*incomplete, *missing]}
        return DjReadinessCheck(
            label="Required metadata",
            status="blocked",
            detail=f"{len(affected_paths)} track(s) need BPM, key, or energy metadata",
        )
    return DjReadinessCheck(
        label="Required metadata",
        status="ready",
        detail="All recommended tracks have BPM, key, and energy metadata",
    )


def _bpm_continuity_check(recommendation: PlaylistRecommendation) -> DjReadinessCheck:
    max_jump = _max_bpm_jump_percent(recommendation)
    if max_jump > MAX_ADJACENT_BPM_DIFFERENCE_PERCENT:
        return DjReadinessCheck(
            label="BPM continuity",
            status="blocked",
            detail=(f"Max adjacent BPM jump is {max_jump:.2f}%, above {MAX_ADJACENT_BPM_DIFFERENCE_PERCENT:.1f}%"),
        )
    return DjReadinessCheck(
        label="BPM continuity",
        status="ready",
        detail=(f"Max adjacent BPM jump is {max_jump:.2f}%, within {MAX_ADJACENT_BPM_DIFFERENCE_PERCENT:.1f}%"),
    )


def _transition_warning_check(recommendation: PlaylistRecommendation) -> DjReadinessCheck:
    warning_count = len(recommendation.warnings) + sum(
        len(score.warnings) for score in recommendation.transition_scores
    )
    if warning_count:
        return DjReadinessCheck(
            label="Transition warnings",
            status="needs_review",
            detail=f"{warning_count} warning(s) need DJ review before export",
        )
    return DjReadinessCheck(
        label="Transition warnings",
        status="ready",
        detail="No recommendation or transition warnings",
    )


def _average_score_check(report: RecommendationQualityReport, minimum_score: float) -> DjReadinessCheck:
    if report.transition_count == 0:
        return DjReadinessCheck(
            label="Average transition score",
            status="blocked",
            detail="No transitions are available to score",
        )
    if report.average_transition_score < minimum_score:
        return DjReadinessCheck(
            label="Average transition score",
            status="needs_review",
            detail=f"Average score {report.average_transition_score:.3f} is below {minimum_score:.2f}",
        )
    return DjReadinessCheck(
        label="Average transition score",
        status="ready",
        detail=f"Average score {report.average_transition_score:.3f} is at or above {minimum_score:.2f}",
    )


def _max_bpm_jump_percent(recommendation: PlaylistRecommendation) -> float:
    return max(
        (
            _bpm_difference_percent(left.bpm or 0.0, right.bpm or 0.0)
            for left, right in zip(recommendation.ordered_tracks, recommendation.ordered_tracks[1:], strict=False)
        ),
        default=0.0,
    )


def _bpm_difference_percent(left_bpm: float, right_bpm: float) -> float:
    lower = min(left_bpm, right_bpm)
    if lower <= 0:
        return 100.0
    return abs(left_bpm - right_bpm) / lower * 100


def _worst_status(statuses: Iterable[ReadinessStatus]) -> ReadinessStatus:
    worst: ReadinessStatus = "ready"
    for status in statuses:
        if _STATUS_RANK[status] > _STATUS_RANK[worst]:
            worst = status
    return worst


__all__ = [
    "DjReadinessCheck",
    "DjReadinessReport",
    "ReadinessStatus",
    "build_dj_readiness_report",
    "format_dj_readiness_summary",
    "validate_serato_round_trip",
]
