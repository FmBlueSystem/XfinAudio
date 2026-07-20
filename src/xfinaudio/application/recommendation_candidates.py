"""Application boundary for desktop recommendation candidate planning."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import build_recommendation_pool, dedupe_recommendation_duplicates
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import prefilter_strategy_candidates


def plan_recommendation_candidates(
    *,
    scanned_records: list[TrackRecord],
    controls: DJControls | None,
    limit: int,
    strategy_name: str | None = None,
) -> list[TrackRecord]:
    """Return the interactive recommendation candidate pool for desktop adapters.

    When ``strategy_name`` is provided, the strategy's hard filters run over the
    FULL library before the interactive cap, so the capped pool contains
    strategy-viable candidates instead of arbitrary scan-order ones.

    Near-duplicate title+artist versions are collapsed to one representative
    each BEFORE the interactive cap (`dedupe_recommendation_duplicates`), so
    the capped pool spends its slots on distinct versions instead of
    duplicates. Control tracks are never removed by this step.
    """
    pool_source = scanned_records
    if strategy_name is not None:
        pool_source = prefilter_strategy_candidates(scanned_records, strategy_name, controls)
    pool_source = dedupe_recommendation_duplicates(pool_source, controls)
    return build_recommendation_pool(pool_source, controls, limit)


__all__ = ["plan_recommendation_candidates"]
