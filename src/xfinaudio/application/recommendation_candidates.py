"""Application boundary for desktop recommendation candidate planning."""

from __future__ import annotations

from dataclasses import dataclass, field

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import build_recommendation_pool, dedupe_recommendation_duplicates
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.energy_arc import traces_an_arc
from xfinaudio.recommendation.playlist_service import (
    COLOR_FILTER_STRATEGIES,
    prefilter_strategy_candidates,
    resolve_color_anchor_path,
)

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


@dataclass(frozen=True)
class RecommendationCandidateContext:
    """Candidate pool plus the bound colour-gate anchor identity.

    The exported `plan_recommendation_candidates` keeps returning a plain list for
    every caller and strategy. Only the colour strategies need the bound anchor
    path transported alongside the records, so it goes through this seam instead
    of changing the public list contract.
    """

    records: list[TrackRecord] = field(default_factory=list)
    color_anchor_path: str | None = None


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
    if strategy_name in COLOR_FILTER_STRATEGIES:
        return plan_recommendation_candidate_context(
            scanned_records=scanned_records, controls=controls, limit=limit, strategy_name=strategy_name
        ).records
    pool_source = scanned_records
    if strategy_name is not None:
        pool_source = prefilter_strategy_candidates(scanned_records, strategy_name, controls)
    pool_source = dedupe_recommendation_duplicates(pool_source, controls)
    # A strategy that traces an arc needs candidates at both ends of the energy
    # range; similarity ranking alone would hand it the anchor's own level.
    spread = traces_an_arc(strategy_name) if strategy_name is not None else False
    return build_recommendation_pool(pool_source, controls, limit, spread_energy=spread)


def plan_recommendation_candidate_context(
    *,
    scanned_records: list[TrackRecord],
    controls: DJControls | None,
    limit: int,
    strategy_name: str,
) -> RecommendationCandidateContext:
    """Plan a colour-strategy pool and bind an immutable anchor identity.

    The anchor path is resolved from the pre-anchor pool ONCE and protected
    through dedupe and the interactive cap, so a duplicate sibling can never
    replace it and the cap can never trim it. `recommend_playlist` then binds that
    exact path in final enforcement instead of re-resolving from the reshaped
    pool — which is what stops the second gate pass emptying a pool the first pass
    had already narrowed for a different anchor.
    """
    anchor_path = resolve_color_anchor_path(scanned_records, strategy_name, controls)
    pool_source = prefilter_strategy_candidates(scanned_records, strategy_name, controls)
    pool_source = dedupe_recommendation_duplicates(pool_source, controls, protected_path=anchor_path)
    spread = traces_an_arc(strategy_name)
    records = build_recommendation_pool(pool_source, controls, limit, spread_energy=spread, protected_path=anchor_path)
    return RecommendationCandidateContext(records=records, color_anchor_path=anchor_path)


__all__ = [
    "RecommendationCandidateContext",
    "plan_recommendation_candidate_context",
    "plan_recommendation_candidates",
]
