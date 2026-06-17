"""Read-only recommendation quality harness.

Measures playlist recommendation quality across a library using scorer-independent metrics:
fill rate, hard-rule transition validity (Camelot adjacency + BPM <= 3%), and energy-curve
monotonicity for directional strategies. The harness never mutates audio, the library, or any
Serato file; it only reads tracks and runs the existing recommendation pipeline.

The transition-validity oracle is implemented here on purpose, independent of the tunable scorer
and of ``build_recommendation_pool`` (the code adjusted in later slices), so it stays an
unbiased reference.
"""

from __future__ import annotations

import random
import statistics

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist
from xfinaudio.recommendation.pool import build_recommendation_pool
from xfinaudio.recommendation.scoring import normalize_genre_tokens
from xfinaudio.recommendation.strategies import get_strategy

_BPM_TOLERANCE_PERCENT = 3.0
_COLLAPSE_THRESHOLD = 3


class EvalConfig(BaseModel):
    """Configuration for a single evaluation run."""

    model_config = ConfigDict(frozen=True)

    seed: int
    sample_size: int
    requested_size: int
    candidate_limit: int = 25
    strategies: tuple[str, ...]
    genre_cohesion: float = 0.0


class StrategyMetrics(BaseModel):
    """Aggregated metrics for one strategy over the sampled anchors."""

    model_config = ConfigDict(frozen=True)

    strategy: str
    samples: int
    mean_fill_rate: float
    collapse_count: int
    mean_transition_validity: float
    mean_energy_monotonicity: float | None
    mean_cross_genre_fraction: float


class EvalReport(BaseModel):
    """Full evaluation report across all requested strategies."""

    model_config = ConfigDict(frozen=True)

    strategies: tuple[StrategyMetrics, ...]

    def render(self) -> str:
        """Render a deterministic, human-readable summary."""
        lines = ["Recommendation quality report", "=" * 30]
        for metrics in sorted(self.strategies, key=lambda m: m.strategy):
            monotonicity = (
                "n/a" if metrics.mean_energy_monotonicity is None else f"{metrics.mean_energy_monotonicity:.3f}"
            )
            lines.append(
                f"{metrics.strategy}: samples={metrics.samples} "
                f"fill={metrics.mean_fill_rate:.3f} "
                f"collapse={metrics.collapse_count} "
                f"validity={metrics.mean_transition_validity:.3f} "
                f"energy_monotonicity={monotonicity} "
                f"cross_genre={metrics.mean_cross_genre_fraction:.3f}"
            )
        return "\n".join(lines)


def _camelot_adjacent(left_key: str | None, right_key: str | None) -> bool:
    """Independent Camelot-wheel adjacency oracle (same key, +/-1 number, or relative major/minor)."""
    if not left_key or not right_key:
        return False
    try:
        left_num, left_letter = int(left_key[:-1]), left_key[-1].upper()
        right_num, right_letter = int(right_key[:-1]), right_key[-1].upper()
    except (ValueError, IndexError):
        return False
    if not (1 <= left_num <= 12 and 1 <= right_num <= 12):
        return False
    if left_letter == right_letter:
        diff = abs(left_num - right_num)
        circular = min(diff, 12 - diff)
        return circular <= 1
    return left_num == right_num


def _bpm_within_tolerance(left_bpm: float | None, right_bpm: float | None) -> bool:
    if left_bpm is None or right_bpm is None or left_bpm <= 0 or right_bpm <= 0:
        return False
    return abs(left_bpm - right_bpm) / min(left_bpm, right_bpm) * 100.0 <= _BPM_TOLERANCE_PERCENT


def _transition_valid(left: TrackRecord, right: TrackRecord) -> bool:
    """A transition is valid only if both Camelot adjacency and BPM tolerance hold."""
    return _camelot_adjacent(left.camelot_key, right.camelot_key) and _bpm_within_tolerance(left.bpm, right.bpm)


def _transition_validity_fraction(ordered: list[TrackRecord]) -> float:
    pairs = list(zip(ordered, ordered[1:], strict=False))
    if not pairs:
        return 1.0
    valid = sum(1 for left, right in pairs if _transition_valid(left, right))
    return valid / len(pairs)


def _fill_rate(track_count: int, requested_size: int) -> float:
    if requested_size <= 0:
        return 0.0
    return min(track_count / requested_size, 1.0)


def _cross_genre_fraction(ordered: list[TrackRecord]) -> float:
    """Fraction of adjacencies whose two tracks have genres that share no token.

    Adjacencies where either track has no genre are ignored (cannot judge). Returns 0.0 when there
    are no judgeable adjacencies. This is the objective "genre mixing" metric for cohesion tuning.
    """
    pairs = list(zip(ordered, ordered[1:], strict=False))
    judgeable = 0
    cross = 0
    for left, right in pairs:
        left_tokens = normalize_genre_tokens(left.genre)
        right_tokens = normalize_genre_tokens(right.genre)
        if not left_tokens or not right_tokens:
            continue
        judgeable += 1
        if not (left_tokens & right_tokens):
            cross += 1
    if judgeable == 0:
        return 0.0
    return cross / judgeable


def _energy_monotonic_fraction(ordered: list[TrackRecord]) -> float:
    pairs = list(zip(ordered, ordered[1:], strict=False))
    if not pairs:
        return 1.0
    monotonic = sum(
        1
        for left, right in pairs
        if left.energy_level is not None and right.energy_level is not None and right.energy_level >= left.energy_level
    )
    return monotonic / len(pairs)


def _sample_anchors(tracks: list[TrackRecord], seed: int, n: int) -> list[TrackRecord]:
    """Deterministically sample up to ``n`` anchor tracks for a given seed."""
    ordered = sorted(tracks, key=lambda t: t.path)
    if n >= len(ordered):
        return ordered
    rng = random.Random(seed)
    return rng.sample(ordered, n)


def evaluate_recommendations(tracks: list[TrackRecord], config: EvalConfig) -> EvalReport:
    """Run every configured strategy over sampled anchors and return aggregated metrics."""
    complete = [t for t in tracks if t.metadata_status == "complete"]
    results: list[StrategyMetrics] = []

    for strategy_name in config.strategies:
        strategy = get_strategy(strategy_name)
        directional = strategy.sort_hint == "energy_ascending"
        anchors = _sample_anchors(complete, config.seed, config.sample_size)

        fill_rates: list[float] = []
        validities: list[float] = []
        monotonicities: list[float] = []
        cross_genre_fractions: list[float] = []
        collapse_count = 0

        for anchor in anchors:
            # Anchor via manual order ("start the set with this track") rather than start_path:
            # start_path can crash recommend_playlist when the BPM-jump guard drops the anchor
            # before sequencing (see optimizer _validate_constraints). manual_order keeps the
            # anchor fixed at the front without that terminal-constraint validation.
            controls = DJControls(manual_order_paths=[anchor.path])
            pool = build_recommendation_pool(complete, controls, config.candidate_limit, strategy=strategy)
            recommendation = recommend_playlist(
                pool, strategy_name, controls=controls, genre_cohesion=config.genre_cohesion
            )
            ordered = recommendation.ordered_tracks

            fill_rates.append(_fill_rate(len(ordered), config.requested_size))
            validities.append(_transition_validity_fraction(ordered))
            cross_genre_fractions.append(_cross_genre_fraction(ordered))
            if len(ordered) < _COLLAPSE_THRESHOLD:
                collapse_count += 1
            if directional:
                monotonicities.append(_energy_monotonic_fraction(ordered))

        results.append(
            StrategyMetrics(
                strategy=strategy_name,
                samples=len(anchors),
                mean_fill_rate=statistics.fmean(fill_rates) if fill_rates else 0.0,
                collapse_count=collapse_count,
                mean_transition_validity=statistics.fmean(validities) if validities else 0.0,
                mean_energy_monotonicity=(statistics.fmean(monotonicities) if monotonicities else None),
                mean_cross_genre_fraction=statistics.fmean(cross_genre_fractions) if cross_genre_fractions else 0.0,
            )
        )

    return EvalReport(strategies=tuple(results))


__all__ = [
    "EvalConfig",
    "EvalReport",
    "StrategyMetrics",
    "evaluate_recommendations",
]
