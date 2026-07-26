"""Deterministic playlist sequence optimization."""

from __future__ import annotations

from collections.abc import Collection

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.camelot import BoostRule
from xfinaudio.recommendation.energy_arc import arc_targets
from xfinaudio.recommendation.scoring import (
    DEFAULT_SCORING_CONFIG,
    DEFAULT_WEIGHTS,
    ScoringWeights,
    TransitionScore,
    TransitionScoringConfig,
    score_transition,
)

# How much the shape of the set weighs against the quality of each transition.
# Transition scores run 0-1, so this is the most a single slot can be penalised
# for sitting at the wrong energy. Low enough that a harmonically broken pair
# never wins on shape alone; high enough to break the tie between two equally
# playable candidates, which is what produced flat sets.
ARC_WEIGHT = 1.0


def _arc_bonuses(
    tracks: list[TrackRecord],
    arc_strategy: str | None,
    arc_weight: float,
    start_path: str | None = None,
    arc_length: int | None = None,
) -> list[list[float]] | None:
    """Return per-track, per-slot adherence scores for the target energy shape.

    ``None`` when no shape is requested, which keeps the solvers on their
    original scoring path.

    ``arc_length`` is how many tracks the DJ will actually play. The curve has
    to span THAT, not the pool it is drawn from: the pool runs about 120 and the
    result is trimmed to the ~15 that fill the slot, so sizing the shape by the
    pool showed the DJ only its first twelve percent. A warm-up never got to
    climb, and `harmonic_journey`'s peak -- two thirds through a 120-slot curve
    -- sat at slot 80, far past the end of the set. Measured on the real
    library: rho +0.386 sized by the pool against +0.806 sized by the set.

    Energy is normalized against the range the pool actually offers, so a set
    drawn from levels 5-8 still traces the full curve inside that band instead
    of being told it is uniformly wrong.
    """
    if arc_strategy is None or arc_weight <= 0 or not tracks:
        return None
    # Normalized against what the optimizer can choose, which excludes the
    # anchor: the DJ's pick is regularly outside the strategy's own band, and
    # one anchor at level 9 over a pool spanning 2-5 stretched the scale to 2-9.
    # The top of the curve then asked for a level nothing in the pool could
    # supply, every candidate scored equally far from it, and the term went
    # inert. Excluding it roughly doubled adherence at every weight tried.
    choosable = [track for track in tracks if track.path != start_path]
    levels = [track.energy_level for track in choosable if track.energy_level is not None]
    if not levels:
        levels = [track.energy_level for track in tracks if track.energy_level is not None]
    if not levels:
        return None
    lowest, highest = min(levels), max(levels)
    span = highest - lowest
    if span == 0:
        return None

    # The anchor holds slot zero, so the shape builds from wherever it sits
    # rather than asking for an opening the DJ's pick cannot provide. Clamped
    # because it is no longer part of the range it is measured against.
    start_at: float | None = None
    if start_path is not None:
        anchor = next((track for track in tracks if track.path == start_path), None)
        if anchor is not None and anchor.energy_level is not None:
            start_at = min(max((anchor.energy_level - lowest) / span, 0.0), 1.0)

    played = max(1, min(arc_length or len(tracks), len(tracks)))
    shape = arc_targets(arc_strategy, length=played, start_at=start_at)
    # Slots past the played set keep the closing target: a candidate parked
    # there is not in the set, so it should not be scored against a curve that
    # has already ended.
    targets = [shape[index] if index < len(shape) else shape[-1] for index in range(len(tracks))]
    bonuses: list[list[float]] = []
    for track in tracks:
        if track.energy_level is None:
            bonuses.append([0.0] * len(tracks))
            continue
        position_value = (track.energy_level - lowest) / span
        bonuses.append([arc_weight * (1.0 - abs(position_value - target)) for target in targets])
    return bonuses


class SequenceRecommendation(BaseModel):
    """Recommended track order with transition explanations."""

    model_config = ConfigDict(frozen=True)

    ordered_tracks: list[TrackRecord]
    transition_scores: list[TransitionScore]
    total_score: float
    optimizer: str


def recommend_sequence(
    tracks: list[TrackRecord],
    start_path: str | None = None,
    end_path: str | None = None,
    exact_limit: int = 15,
    boost_rules: Collection[BoostRule] | None = None,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    cache: dict[tuple, TransitionScore] | None = None,
    config: TransitionScoringConfig | None = None,
    arc_strategy: str | None = None,
    arc_weight: float = ARC_WEIGHT,
    arc_length: int | None = None,
    max_bpm_difference_percent: float | None = None,
) -> SequenceRecommendation:
    """Recommend a deterministic track ordering that maximizes adjacent transition scores.

    An optional session-scoped ``cache`` is threaded into every ``score_transition``
    call so the score matrix and the final transition scores share memoized results.
    """
    if not tracks:
        return SequenceRecommendation(ordered_tracks=[], transition_scores=[], total_score=0.0, optimizer="empty")
    _validate_constraints(tracks, start_path, end_path)

    scoring_config = config or DEFAULT_SCORING_CONFIG
    ordered = sorted(tracks, key=lambda track: track.path)
    score_matrix = _score_matrix(ordered, boost_rules, weights, scoring_config, cache, max_bpm_difference_percent)
    arc = _arc_bonuses(ordered, arc_strategy, arc_weight, start_path, arc_length)
    if len(ordered) <= exact_limit:
        path_indexes = _exact_path(ordered, score_matrix, start_path, end_path, arc)
        optimizer = "exact"
    else:
        path_indexes = _heuristic_path(ordered, score_matrix, start_path, end_path, arc)
        optimizer = "greedy-2opt"

    ordered_tracks = [ordered[index] for index in path_indexes]
    transition_scores = [
        score_transition(left, right, weights=weights, boost_rules=boost_rules, cache=cache, config=scoring_config)
        for left, right in zip(ordered_tracks, ordered_tracks[1:], strict=False)
    ]
    return SequenceRecommendation(
        ordered_tracks=ordered_tracks,
        transition_scores=transition_scores,
        total_score=sum(score.total_score for score in transition_scores),
        optimizer=optimizer,
    )


def _validate_constraints(tracks: list[TrackRecord], start_path: str | None, end_path: str | None) -> None:
    paths = {track.path for track in tracks}
    if start_path is not None and start_path not in paths:
        raise ValueError(f"Unknown start_path: {start_path}")
    if end_path is not None and end_path not in paths:
        raise ValueError(f"Unknown end_path: {end_path}")
    if start_path is not None and end_path is not None and start_path == end_path and len(tracks) > 1:
        raise ValueError("start_path and end_path must differ when sequencing multiple tracks")


# Charged for an adjacency the DJ cannot beatmatch. Large enough that no
# combination of harmony, energy and shape can pay for one, so the solvers route
# around it or leave the track out; finite so a set with no alternative still
# produces an order rather than nothing at all.
UNPLAYABLE_TRANSITION_PENALTY = -1000.0


def _score_matrix(
    tracks: list[TrackRecord],
    boost_rules: Collection[BoostRule] | None,
    weights: ScoringWeights,
    config: TransitionScoringConfig,
    cache: dict[tuple, TransitionScore] | None = None,
    max_bpm_difference_percent: float | None = None,
) -> list[list[float]]:
    """Score every ordered pair, with unplayable tempo jumps priced out.

    The BPM difference used to be a scoring component and nothing more, so a
    138 could follow a 120 whenever the harmony was good enough to pay for it.
    On the real library 11 of 12 peak-time sets carried a jump above the
    declared 3% ceiling, the worst of them 47.89% -- a CDJ's pitch fader is
    +/-6% or +/-8%, and 6% already moves the key a full semitone.

    Making it a price rather than a filter keeps the solvers whole: they route
    around the pair, or leave a stranded track out, instead of the caller
    pruning a sequence after the fact and handing back a shorter set.
    """
    return [
        [
            0.0
            if left == right
            else _pair_score(left, right, boost_rules, weights, config, cache, max_bpm_difference_percent)
            for right in tracks
        ]
        for left in tracks
    ]


def _pair_score(
    left: TrackRecord,
    right: TrackRecord,
    boost_rules: Collection[BoostRule] | None,
    weights: ScoringWeights,
    config: TransitionScoringConfig,
    cache: dict[tuple, TransitionScore] | None,
    max_bpm_difference_percent: float | None,
) -> float:
    score = score_transition(
        left, right, weights=weights, boost_rules=boost_rules, cache=cache, config=config
    ).total_score
    if max_bpm_difference_percent is None or left.bpm is None or right.bpm is None or not left.bpm:
        return score
    if abs(right.bpm - left.bpm) / left.bpm * 100.0 > max_bpm_difference_percent:
        return score + UNPLAYABLE_TRANSITION_PENALTY
    return score


def _exact_path(
    tracks: list[TrackRecord],
    score_matrix: list[list[float]],
    start_path: str | None,
    end_path: str | None,
    arc: list[list[float]] | None = None,
) -> tuple[int, ...]:
    path_by_index = {track.path: index for index, track in enumerate(tracks)}
    start_indexes = [path_by_index[start_path]] if start_path is not None else list(range(len(tracks)))
    end_index = path_by_index[end_path] if end_path is not None else None

    states: dict[tuple[int, int], float] = {}
    parents: dict[tuple[int, int], tuple[int, int] | None] = {}
    for index in start_indexes:
        key = (1 << index, index)
        states[key] = arc[index][0] if arc else 0.0
        parents[key] = None

    full_mask = (1 << len(tracks)) - 1
    # The layer index is the slot being filled, which is what the arc scores.
    for slot in range(1, len(tracks)):
        next_states: dict[tuple[int, int], float] = {}
        next_parents: dict[tuple[int, int], tuple[int, int] | None] = {}
        for (mask, last), score in states.items():
            for candidate in range(len(tracks)):
                if mask & (1 << candidate):
                    continue
                next_mask = mask | (1 << candidate)
                if end_index is not None and candidate == end_index and next_mask != full_mask:
                    continue
                key = (next_mask, candidate)
                next_score = score + score_matrix[last][candidate]
                if arc:
                    next_score += arc[candidate][slot]
                parent_key = (mask, last)
                if _state_is_better(next_score, key, next_states):
                    next_states[key] = next_score
                    next_parents[key] = parent_key
        parents.update(next_parents)
        states = next_states

    candidate_keys = [key for key in states if key[0] == full_mask and (end_index is None or key[1] == end_index)]
    best_score = max(states[key] for key in candidate_keys)
    best_keys = [key for key in candidate_keys if states[key] == best_score]
    return min((_reconstruct_path(parents, key) for key in best_keys), key=lambda path: _path_key(path, tracks))


def _heuristic_path(
    tracks: list[TrackRecord],
    score_matrix: list[list[float]],
    start_path: str | None,
    end_path: str | None,
    arc: list[list[float]] | None = None,
) -> tuple[int, ...]:
    path_by_index = {track.path: index for index, track in enumerate(tracks)}
    end_index = path_by_index[end_path] if end_path is not None else None
    current = path_by_index[start_path] if start_path is not None else 0
    remaining = set(range(len(tracks)))
    remaining.remove(current)
    if end_index is not None and end_index in remaining:
        remaining.remove(end_index)

    path = [current]
    while remaining:
        slot = len(path)
        candidate = min(
            remaining,
            key=lambda index: (
                -(score_matrix[current][index] + (arc[index][slot] if arc else 0.0)),
                tracks[index].path,
            ),
        )
        path.append(candidate)
        remaining.remove(candidate)
        current = candidate
    if end_index is not None and end_index not in path:
        path.append(end_index)

    return _two_opt(
        tuple(path),
        score_matrix,
        tracks,
        start_fixed=start_path is not None,
        end_fixed=end_path is not None,
        arc=arc,
    )


def _two_opt(
    path: tuple[int, ...],
    score_matrix: list[list[float]],
    tracks: list[TrackRecord],
    *,
    start_fixed: bool,
    end_fixed: bool,
    arc: list[list[float]] | None = None,
) -> tuple[int, ...]:
    best = path
    improved = True
    while improved:
        improved = False
        start = 1 if start_fixed else 0
        stop = len(best) - 1 if end_fixed else len(best)
        for left in range(start, stop - 1):
            for right in range(left + 1, stop):
                candidate = (*best[:left], *reversed(best[left : right + 1]), *best[right + 1 :])
                if _path_is_better(candidate, best, score_matrix, tracks, arc):
                    best = candidate
                    improved = True
                    break
            if improved:
                break
    return best


def _path_score(path: tuple[int, ...], score_matrix: list[list[float]], arc: list[list[float]] | None = None) -> float:
    total = sum(score_matrix[left][right] for left, right in zip(path, path[1:], strict=False))
    if arc:
        total += sum(arc[track_index][slot] for slot, track_index in enumerate(path))
    return total


def _path_is_better(
    candidate: tuple[int, ...],
    current: tuple[int, ...],
    score_matrix: list[list[float]],
    tracks: list[TrackRecord],
    arc: list[list[float]] | None = None,
) -> bool:
    candidate_score = _path_score(candidate, score_matrix, arc)
    current_score = _path_score(current, score_matrix, arc)
    if candidate_score > current_score:
        return True
    return candidate_score == current_score and _path_key(candidate, tracks) < _path_key(current, tracks)


def _state_is_better(
    score: float,
    key: tuple[int, int],
    next_states: dict[tuple[int, int], float],
) -> bool:
    current_score = next_states.get(key)
    if current_score is None:
        return True
    return score > current_score


def _reconstruct_path(
    parents: dict[tuple[int, int], tuple[int, int] | None],
    key: tuple[int, int],
) -> tuple[int, ...]:
    path: list[int] = []
    current: tuple[int, int] | None = key
    while current is not None:
        path.append(current[1])
        current = parents[current]
    return tuple(reversed(path))


def _path_key(path: tuple[int, ...], tracks: list[TrackRecord]) -> tuple[str, ...]:
    return tuple(tracks[index].path for index in path)
