"""Application boundary for desktop recommendation candidate planning."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import build_recommendation_pool
from xfinaudio.recommendation.controls import DJControls


def plan_recommendation_candidates(
    *,
    scanned_records: list[TrackRecord],
    controls: DJControls | None,
    limit: int,
) -> list[TrackRecord]:
    """Return the interactive recommendation candidate pool for desktop adapters."""
    return build_recommendation_pool(scanned_records, controls, limit)


__all__ = ["plan_recommendation_candidates"]
