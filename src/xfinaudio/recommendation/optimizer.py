"""Deterministic playlist sequence optimization."""

from __future__ import annotations

from collections.abc import Collection

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.camelot import BoostRule
from xfinaudio.recommendation.scoring import (
    DEFAULT_SCORING_CONFIG,
    DEFAULT_WEIGHTS,
    ScoringWeights,
    TransitionScore,
    TransitionScoringConfig,
    score_transition,
)


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
    score_matrix = _score_matrix(ordered, boost_rules, weights, scoring_config, cache)
    if len(ordered) <= exact_limit:
        path_indexes = _exact_path(ordered, score_matrix, start_path, end_path)
        optimizer = "exact"
    else:
        path_indexes = _heuristic_path(ordered, score_matrix, start_path, end_path)
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


def _score_matrix(
    tracks: list[TrackRecord],
    boost_rules: Collection[BoostRule] | None,
    weights: ScoringWeights,
    config: TransitionScoringConfig,
    cache: dict[tuple, TransitionScore] | None = None,
) -> list[list[float]]:
    return [
        [
            0.0
            if left == right
            else score_transition(
                left, right, weights=weights, boost_rules=boost_rules, cache=cache, config=config
            ).total_score
            for right in tracks
        ]
        for left in tracks
    ]


def _exact_path(
    tracks: list[TrackRecord],
    score_matrix: list[list[float]],
    start_path: str | None,
    end_path: str | None,
) -> tuple[int, ...]:
    path_by_index = {track.path: index for index, track in enumerate(tracks)}
    start_indexes = [path_by_index[start_path]] if start_path is not None else list(range(len(tracks)))
    end_index = path_by_index[end_path] if end_path is not None else None

    states: dict[tuple[int, int], float] = {}
    parents: dict[tuple[int, int], tuple[int, int] | None] = {}
    for index in start_indexes:
        key = (1 << index, index)
        states[key] = 0.0
        parents[key] = None

    full_mask = (1 << len(tracks)) - 1
    for _ in range(1, len(tracks)):
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
        candidate = min(remaining, key=lambda index: (-score_matrix[current][index], tracks[index].path))
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
    )


def _two_opt(
    path: tuple[int, ...],
    score_matrix: list[list[float]],
    tracks: list[TrackRecord],
    *,
    start_fixed: bool,
    end_fixed: bool,
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
                if _path_is_better(candidate, best, score_matrix, tracks):
                    best = candidate
                    improved = True
                    break
            if improved:
                break
    return best


def _path_score(path: tuple[int, ...], score_matrix: list[list[float]]) -> float:
    return sum(score_matrix[left][right] for left, right in zip(path, path[1:], strict=False))


def _path_is_better(
    candidate: tuple[int, ...],
    current: tuple[int, ...],
    score_matrix: list[list[float]],
    tracks: list[TrackRecord],
) -> bool:
    candidate_score = _path_score(candidate, score_matrix)
    current_score = _path_score(current, score_matrix)
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
