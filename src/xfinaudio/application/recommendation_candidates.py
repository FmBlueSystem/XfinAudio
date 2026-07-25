"""Application boundary for desktop recommendation candidate planning."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import build_recommendation_pool, dedupe_recommendation_duplicates
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import prefilter_strategy_candidates

# How many candidates the optimizer gets per track it will actually place.
# Measured on a 10,367-track library with a 30-minute slot at two minutes per
# track (15 tracks): mean transition score ran 0.8811 at a pool of 50, 0.8936 at
# 80, 0.9057 at 120. More options genuinely help -- the earlier reading that
# quality peaked at 50 came from trimming to a fixed count of 10, not from
# filling a slot.
_CANDIDATES_PER_PLACED_TRACK = 8
# Past this the gain stops paying: a pool of 160 scored 0.9083 against 0.9057 at
# 120, a third of a percent, for 2.33s per set against 0.93s.
_MAX_POOL = 150
_MIN_POOL = 25


def pool_size_for_slot(*, slot_minutes: float, played_seconds_per_track: float) -> int:
    """Return how many candidates to gather for a slot of this length.

    A fixed pool cannot serve both a 30-minute and a 3-hour set: at 50 the track
    count bottomed out at 11 whatever the slot, because compatible candidates
    ran out before the slot filled.
    """
    expected_tracks = max(1.0, slot_minutes * 60 / max(played_seconds_per_track, 1.0))
    return int(min(_MAX_POOL, max(_MIN_POOL, expected_tracks * _CANDIDATES_PER_PLACED_TRACK)))


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
