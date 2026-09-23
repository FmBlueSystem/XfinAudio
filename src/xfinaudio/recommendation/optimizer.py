"""Deterministic playlist sequence optimization."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import deque
from collections.abc import Collection
from functools import lru_cache
from heapq import nsmallest

from pydantic import BaseModel, ConfigDict, Field

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.camelot import BoostRule
from xfinaudio.recommendation.energy_arc import arc_targets
from xfinaudio.recommendation.scoring import (
    DEFAULT_SCORING_CONFIG,
    ScoringWeights,
    TransitionScore,
    TransitionScoringConfig,
    bpm_difference_percent,
    score_transition,
)
from xfinaudio.recommendation.scoring import (
    DEFAULT_WEIGHTS as DEFAULT_WEIGHTS,
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
    warnings: list[str] = Field(default_factory=list)


def recommend_sequence(
    tracks: list[TrackRecord],
    start_path: str | None = None,
    end_path: str | None = None,
    exact_limit: int = 15,
    boost_rules: Collection[BoostRule] | None = None,
    weights: ScoringWeights | None = None,
    cache: dict[tuple, TransitionScore] | None = None,
    config: TransitionScoringConfig | None = None,
    arc_strategy: str | None = None,
    arc_weight: float = ARC_WEIGHT,
    arc_length: int | None = None,
    max_bpm_difference_percent: float | None = None,
    target_length: int | None = None,
    mandatory_paths: Collection[str] | None = None,
    external_start: TrackRecord | None = None,
    arc_slot_offset: int = 0,
    beam_width: int = 64,
) -> SequenceRecommendation:
    """Recommend a deterministic track ordering that maximizes adjacent transition scores.

    An optional session-scoped ``cache`` is threaded into every ``score_transition``
    call so the score matrix and the final transition scores share memoized results.
    """
    if not tracks:
        return SequenceRecommendation(ordered_tracks=[], transition_scores=[], total_score=0.0, optimizer="empty")

    scoring_config = config or DEFAULT_SCORING_CONFIG
    ordered = sorted(tracks, key=lambda track: track.path)
    if arc_strategy is not None and max_bpm_difference_percent is not None and arc_length is not None:
        return _arc_subset_recommendation(
            ordered,
            start_path=start_path,
            end_path=end_path,
            exact_limit=exact_limit,
            boost_rules=boost_rules,
            weights=weights,
            cache=cache,
            config=scoring_config,
            arc_strategy=arc_strategy,
            arc_weight=arc_weight,
            arc_length=arc_length,
            max_bpm_difference_percent=max_bpm_difference_percent,
            target_length=target_length,
            mandatory_paths=mandatory_paths,
            external_start=external_start,
            arc_slot_offset=arc_slot_offset,
            beam_width=beam_width,
        )

    _validate_constraints(ordered, start_path, end_path)
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


def _arc_subset_recommendation(
    tracks: list[TrackRecord],
    *,
    start_path: str | None,
    end_path: str | None,
    exact_limit: int,
    boost_rules: Collection[BoostRule] | None,
    weights: ScoringWeights | None,
    cache: dict[tuple, TransitionScore] | None,
    config: TransitionScoringConfig,
    arc_strategy: str,
    arc_weight: float,
    arc_length: int,
    max_bpm_difference_percent: float,
    target_length: int | None,
    mandatory_paths: Collection[str] | None,
    external_start: TrackRecord | None,
    arc_slot_offset: int,
    beam_width: int,
) -> SequenceRecommendation:
    """Select and order a target-length arc without materializing score matrices."""
    by_path = {track.path: index for index, track in enumerate(tracks)}
    mandatory = set(mandatory_paths or ())
    if start_path is not None:
        mandatory.add(start_path)
    if end_path is not None:
        mandatory.add(end_path)
    missing = sorted(path for path in mandatory if path not in by_path)
    optimizer_name = "arc-subset-exact" if len(tracks) <= exact_limit else "arc-subset-beam"
    if missing:
        return _empty_subset_result(
            optimizer_name,
            f"Arc subset proven infeasible: mandatory path(s) not in the candidate pool: {', '.join(missing)}",
        )

    target = arc_length if target_length is None else max(0, target_length)
    if len(mandatory) > target:
        return _empty_subset_result(
            optimizer_name,
            f"Arc subset proven infeasible: {len(mandatory)} mandatory paths exceed target length {target}",
        )
    if target == 0:
        return SequenceRecommendation(
            ordered_tracks=[], transition_scores=[], total_score=0.0, optimizer=optimizer_name
        )
    if start_path == end_path and target > 1 and start_path is not None:
        return _empty_subset_result(
            optimizer_name,
            "Arc subset proven infeasible: one path cannot be both start and terminal for a multi-track target",
        )

    neighbors, universal_neighbors, expand_frontier = _lazy_bpm_neighbors(tracks, max_bpm_difference_percent)
    start_index = by_path.get(start_path) if start_path is not None else None
    end_index = by_path.get(end_path) if end_path is not None else None
    mandatory_mask = sum(1 << by_path[path] for path in mandatory)

    initial_indexes = _subset_initial_indexes(
        tracks,
        start_index,
        end_index,
        target,
        external_start,
        neighbors,
        max_bpm_difference_percent,
    )
    if not initial_indexes:
        return _empty_subset_result(
            optimizer_name,
            "Arc subset proven infeasible: no candidate is BPM-compatible with the required start seam",
        )

    reachable, hops_from_start = _reachable_indices(
        initial_indexes,
        expand_frontier,
        target - 1,
        universe_size=len(tracks),
        universal_neighbors=universal_neighbors,
    )
    if end_index is not None and end_index not in reachable:
        return _empty_subset_result(
            optimizer_name,
            "Arc subset proven infeasible: required end_path is unreachable within the available hops",
        )
    unreachable_mandatory = sorted(
        tracks[index].path for index in range(len(tracks)) if mandatory_mask & (1 << index) and index not in reachable
    )
    if unreachable_mandatory:
        return _empty_subset_result(
            optimizer_name,
            "Arc subset proven infeasible: mandatory paths cannot coexist in one BPM-valid path: "
            + ", ".join(unreachable_mandatory),
        )
    if len(reachable) < target:
        return _empty_subset_result(
            optimizer_name,
            f"Arc subset proven infeasible: only {len(reachable)} BPM-reachable candidates for target length {target}",
        )

    def reachable_neighbors(index: int):
        return (candidate for candidate in neighbors(index) if candidate in reachable)

    hops_to_end = _hop_distances(end_index, reachable_neighbors) if end_index is not None else {}
    search_domain = (
        {index for index in reachable if hops_from_start[index] + hops_to_end.get(index, target + 1) <= target - 1}
        if end_index is not None
        else reachable
    )
    search_domain_mask = sum(1 << index for index in search_domain)
    if mandatory_mask & search_domain_mask != mandatory_mask:
        return _empty_subset_result(
            optimizer_name,
            "Arc subset proven infeasible: mandatory paths cannot satisfy the fixed-end hop budget",
        )
    if len(search_domain) < target:
        return _empty_subset_result(
            optimizer_name,
            f"Arc subset proven infeasible: only {len(search_domain)} candidates satisfy the fixed-end hop budget",
        )

    def domain_neighbors(index: int):
        return (candidate for candidate in neighbors(index) if candidate in search_domain)

    initial_indexes = tuple(index for index in initial_indexes if index in search_domain)
    normalization_domain = search_domain - ({start_index} if start_index is not None else set())
    arc_bonus = _lazy_arc_bonus(
        tracks,
        normalization_domain,
        arc_strategy,
        arc_weight,
        arc_length,
        arc_slot_offset,
        external_start or (tracks[start_index] if start_index is not None else None),
    )

    @lru_cache(maxsize=131_072)
    def transition(left: int | None, right: int) -> float:
        left_track = external_start if left is None else tracks[left]
        if left_track is None:
            return 0.0
        return score_transition(
            left_track,
            tracks[right],
            weights=weights,
            boost_rules=boost_rules,
            cache=None,
            config=config,
        ).total_score

    if len(search_domain) <= exact_limit:
        path = _exact_arc_subset_path(
            tracks,
            target,
            initial_indexes,
            end_index,
            mandatory_mask,
            domain_neighbors,
            hops_to_end,
            transition,
            arc_bonus,
        )
        optimizer_name = "arc-subset-exact"
        exhausted = False
    else:
        path, exhausted = _beam_arc_subset_path(
            tracks,
            target,
            initial_indexes,
            end_index,
            mandatory_mask,
            domain_neighbors,
            hops_to_end,
            transition,
            arc_bonus,
            beam_width,
            len(search_domain),
        )
        if path is None and exhausted and beam_width > 0 and len(search_domain) <= 128:
            # A capped desktop pool can be small yet still need a low-scoring
            # connector path that a K=64 beam prunes. Retry only after failure;
            # successful capped calls and large raw domains keep the cheap path.
            retry_width = min(16_384, max(beam_width, len(search_domain) ** 2 * 2))
            path, exhausted = _beam_arc_subset_path(
                tracks,
                target,
                initial_indexes,
                end_index,
                mandatory_mask,
                domain_neighbors,
                hops_to_end,
                transition,
                arc_bonus,
                retry_width,
                len(search_domain),
            )
        optimizer_name = "arc-subset-beam"

    if path is None:
        if exhausted:
            return _empty_subset_result(
                optimizer_name,
                "Arc subset beam search budget exhausted without a full path; this is not proof that none exists",
            )
        return _empty_subset_result(
            optimizer_name,
            "Arc subset proven infeasible: no BPM-valid target-length path satisfies every mandatory control",
        )

    ordered_tracks = [tracks[index] for index in path]
    transition_scores = [
        score_transition(left, right, weights=weights, boost_rules=boost_rules, cache=cache, config=config)
        for left, right in zip(ordered_tracks, ordered_tracks[1:], strict=False)
    ]
    return SequenceRecommendation(
        ordered_tracks=ordered_tracks,
        transition_scores=transition_scores,
        total_score=sum(score.total_score for score in transition_scores),
        optimizer=optimizer_name,
    )


def _empty_subset_result(optimizer: str, warning: str) -> SequenceRecommendation:
    return SequenceRecommendation(
        ordered_tracks=[], transition_scores=[], total_score=0.0, optimizer=optimizer, warnings=[warning]
    )


def _edge_is_playable(left: TrackRecord, right: TrackRecord, ceiling: float) -> bool:
    if left.bpm is None or right.bpm is None or not left.bpm or not right.bpm:
        return True
    return bpm_difference_percent(left.bpm, right.bpm) <= ceiling


def _lazy_bpm_neighbors(tracks: list[TrackRecord], ceiling: float):
    measurable = sorted(
        ((track.bpm or 0.0, index) for index, track in enumerate(tracks) if track.bpm is not None and track.bpm > 0),
        key=lambda item: (item[0], tracks[item[1]].path),
    )
    bpms = [item[0] for item in measurable]
    unknown = frozenset(index for index, track in enumerate(tracks) if track.bpm is None or not track.bpm)
    margin = ceiling / max(1.0, 100.0 - ceiling)

    def bpm_windows(bpm: float) -> tuple[tuple[float, float], ...]:
        return tuple((center * (1.0 - margin), center * (1.0 + margin)) for center in (bpm, bpm / 2.0, bpm * 2.0))

    @lru_cache(maxsize=512)
    def neighbors(index: int) -> Collection[int]:
        bpm = tracks[index].bpm
        if bpm is None or not bpm:
            # Unknown BPM is a pass-through edge to every candidate. A range
            # represents that universal adjacency without retaining N indexes.
            return range(len(tracks))
        else:
            found = set(unknown)
            for low, high in bpm_windows(bpm):
                for position in range(bisect_left(bpms, low), bisect_right(bpms, high)):
                    found.add(measurable[position][1])
            candidates = found
        result = tuple(
            candidate
            for candidate in sorted(candidates, key=lambda item: tracks[item].path)
            if candidate != index and _edge_is_playable(tracks[index], tracks[candidate], ceiling)
        )
        return result

    def expand_frontier(frontier: set[int]) -> set[int]:
        """Return a hop frontier without constructing every node's adjacency."""
        if frontier & unknown:
            return set(range(len(tracks)))
        intervals = sorted(
            interval
            for index in frontier
            if (bpm := tracks[index].bpm) is not None and bpm > 0
            for interval in bpm_windows(bpm)
        )
        merged: list[tuple[float, float]] = []
        for low, high in intervals:
            if merged and low <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], high))
            else:
                merged.append((low, high))

        possible = set(unknown)
        for low, high in merged:
            possible.update(
                measurable[position][1] for position in range(bisect_left(bpms, low), bisect_right(bpms, high))
            )
        frontier_measurable = sorted(
            ((tracks[index].bpm or 0.0, index) for index in frontier),
            key=lambda item: (item[0], tracks[item[1]].path),
        )
        frontier_bpms = [item[0] for item in frontier_measurable]

        def has_frontier_edge(candidate: int) -> bool:
            bpm = tracks[candidate].bpm
            if bpm is None or not bpm:
                return True
            for low, high in bpm_windows(bpm):
                for position in range(bisect_left(frontier_bpms, low), bisect_right(frontier_bpms, high)):
                    source = frontier_measurable[position][1]
                    if _edge_is_playable(tracks[source], tracks[candidate], ceiling):
                        return True
            return False

        # The merged windows are a fast superset. Validate against the real
        # folded comparator so their approximation never invents an edge.
        return {candidate for candidate in possible if has_frontier_edge(candidate)}

    return neighbors, unknown, expand_frontier


def _subset_initial_indexes(
    tracks: list[TrackRecord],
    start_index: int | None,
    end_index: int | None,
    target: int,
    external_start: TrackRecord | None,
    neighbors,
    ceiling: float = 3.0,
) -> tuple[int, ...]:
    if start_index is not None:
        return (start_index,)
    candidates = range(len(tracks))
    if external_start is not None:
        candidates = (index for index in candidates if _edge_is_playable(external_start, tracks[index], ceiling))
    return tuple(
        index
        for index in sorted(candidates, key=lambda item: tracks[item].path)
        if end_index is None or index != end_index or target == 1
    )


def _reachable_indices(
    initial: Collection[int],
    expand_frontier,
    max_hops: int,
    *,
    universe_size: int,
    universal_neighbors: Collection[int],
) -> tuple[set[int], dict[int, int]]:
    reached = set(initial)
    frontier = set(initial)
    distances = dict.fromkeys(initial, 0)
    if len(reached) == universe_size:
        return reached, distances
    universal = set(universal_neighbors)
    for hop in range(max_hops):
        if frontier & universal:
            for index in range(universe_size):
                distances.setdefault(index, hop + 1)
            return set(range(universe_size)), distances
        frontier = expand_frontier(frontier) - reached
        if not frontier:
            break
        for index in frontier:
            distances[index] = hop + 1
        reached.update(frontier)
        if len(reached) == universe_size:
            break
    return reached, distances


def _hop_distances(end_index: int | None, neighbors) -> dict[int, int]:
    if end_index is None:
        return {}
    distances = {end_index: 0}
    queue = deque([end_index])
    while queue:
        current = queue.popleft()
        for candidate in neighbors(current):
            if candidate not in distances:
                distances[candidate] = distances[current] + 1
                queue.append(candidate)
    return distances


def _lazy_arc_bonus(
    tracks: list[TrackRecord],
    domain: set[int],
    strategy: str,
    weight: float,
    arc_length: int,
    slot_offset: int,
    root: TrackRecord | None,
):
    levels = [level for index in domain if (level := tracks[index].energy_level) is not None]
    if not levels or weight <= 0:
        return lambda _index, _slot: 0.0
    lowest, highest = min(levels), max(levels)
    span = highest - lowest
    if span == 0:
        return lambda _index, _slot: 0.0
    start_at = None
    if root is not None and root.energy_level is not None:
        start_at = min(max((root.energy_level - lowest) / span, 0.0), 1.0)
    shape = arc_targets(strategy, length=max(1, arc_length), start_at=start_at)
    memo: dict[tuple[int, int], float] = {}

    def bonus(index: int, local_slot: int) -> float:
        key = (index, local_slot)
        if key not in memo:
            level = tracks[index].energy_level
            if level is None:
                memo[key] = 0.0
            else:
                slot = min(slot_offset + local_slot, len(shape) - 1)
                position = (level - lowest) / span
                memo[key] = weight * (1.0 - abs(position - shape[slot]))
        return memo[key]

    return bonus


def _state_can_finish(
    mask: int,
    last: int,
    length: int,
    target: int,
    mandatory_mask: int,
    end_index: int | None,
    hops_to_end: dict[int, int],
) -> bool:
    remaining = target - length
    missing_mandatory = (mandatory_mask & ~mask).bit_count()
    if missing_mandatory > remaining:
        return False
    if end_index is not None:
        distance = hops_to_end.get(last)
        if distance is None or distance > remaining:
            return False
    return True


def _exact_arc_subset_path(
    tracks: list[TrackRecord],
    target: int,
    initial: tuple[int, ...],
    end_index: int | None,
    mandatory_mask: int,
    neighbors,
    hops_to_end: dict[int, int],
    transition,
    arc_bonus,
) -> tuple[int, ...] | None:
    states: dict[tuple[int, int], tuple[float, tuple[int, ...]]] = {}
    for index in initial:
        mask = 1 << index
        if _state_can_finish(mask, index, 1, target, mandatory_mask, end_index, hops_to_end):
            states[(mask, index)] = (transition(None, index) + arc_bonus(index, 0), (index,))
    for slot in range(1, target):
        next_states: dict[tuple[int, int], tuple[float, tuple[int, ...]]] = {}
        for (mask, last), (score, path) in states.items():
            for candidate in neighbors(last):
                if mask & (1 << candidate):
                    continue
                if end_index is not None and candidate == end_index and slot != target - 1:
                    continue
                next_mask = mask | (1 << candidate)
                if not _state_can_finish(
                    next_mask, candidate, slot + 1, target, mandatory_mask, end_index, hops_to_end
                ):
                    continue
                next_path = (*path, candidate)
                next_score = score + transition(last, candidate) + arc_bonus(candidate, slot)
                key = (next_mask, candidate)
                current = next_states.get(key)
                if (
                    current is None
                    or next_score > current[0]
                    or (next_score == current[0] and _path_key(next_path, tracks) < _path_key(current[1], tracks))
                ):
                    next_states[key] = (next_score, next_path)
        states = next_states
    valid = [
        value
        for (mask, last), value in states.items()
        if mask & mandatory_mask == mandatory_mask and (end_index is None or last == end_index)
    ]
    if not valid:
        return None
    return min(valid, key=lambda item: (-item[0], _path_key(item[1], tracks)))[1]


def _beam_arc_subset_path(
    tracks: list[TrackRecord],
    target: int,
    initial: tuple[int, ...],
    end_index: int | None,
    mandatory_mask: int,
    neighbors,
    hops_to_end: dict[int, int],
    transition,
    arc_bonus,
    beam_width: int,
    candidate_domain_size: int,
) -> tuple[tuple[int, ...] | None, bool]:
    if beam_width <= 0:
        return None, True

    def rank(item: tuple[float, int, int, tuple[int, ...]]):
        return -item[0], _path_key(item[3], tracks)

    states = nsmallest(
        beam_width,
        (
            (transition(None, index) + arc_bonus(index, 0), 1 << index, index, (index,))
            for index in initial
            if _state_can_finish(1 << index, index, 1, target, mandatory_mask, end_index, hops_to_end)
        ),
        key=rank,
    )
    # Desktop-capped domains are small enough to score exhaustively. Applying
    # the raw-library preselection there can hide the one low-arc-bonus bridge
    # whose transition quality makes the complete path possible.
    successor_budget = len(tracks) if candidate_domain_size <= 256 else beam_width
    mandatory_indexes = [index for index in range(len(tracks)) if mandatory_mask & (1 << index)]
    for slot in range(1, target):
        expanded: list[tuple[float, int, int, tuple[int, ...]]] = []
        for score, mask, last, path in states:
            neighbor_candidates = neighbors(last)
            mandatory_successors: list[tuple[int, int]] = []
            for candidate in mandatory_indexes:
                if mask & (1 << candidate):
                    continue
                if end_index is not None and candidate == end_index and slot != target - 1:
                    continue
                if candidate not in neighbor_candidates:
                    continue
                next_mask = mask | (1 << candidate)
                if not _state_can_finish(
                    next_mask, candidate, slot + 1, target, mandatory_mask, end_index, hops_to_end
                ):
                    continue
                mandatory_successors.append((candidate, next_mask))

            def optional_successors(
                neighbor_candidates=neighbor_candidates,
                mask=mask,
                slot=slot,
            ):
                for candidate in neighbor_candidates:
                    if mandatory_mask & (1 << candidate) or mask & (1 << candidate):
                        continue
                    if end_index is not None and candidate == end_index and slot != target - 1:
                        continue
                    next_mask = mask | (1 << candidate)
                    if _state_can_finish(
                        next_mask, candidate, slot + 1, target, mandatory_mask, end_index, hops_to_end
                    ):
                        yield candidate, next_mask

            optional_budget = max(0, successor_budget - len(mandatory_successors))
            selected_successors = [
                *sorted(mandatory_successors, key=lambda item: tracks[item[0]].path),
                *nsmallest(
                    optional_budget,
                    optional_successors(),
                    key=lambda item: (-arc_bonus(item[0], slot), tracks[item[0]].path),
                ),
            ]

            def successors(
                score=score,
                last=last,
                path=path,
                slot=slot,
                selected_successors=selected_successors,
            ):
                for candidate, next_mask in selected_successors:
                    yield (
                        score + transition(last, candidate) + arc_bonus(candidate, slot),
                        next_mask,
                        candidate,
                        (*path, candidate),
                    )

            expanded.extend(nsmallest(beam_width, successors(), key=rank))
        if not expanded:
            return None, True
        states = nsmallest(beam_width, expanded, key=rank)
    valid = [
        item
        for item in states
        if item[1] & mandatory_mask == mandatory_mask and (end_index is None or item[2] == end_index)
    ]
    if not valid:
        return None, True
    return min(valid, key=rank)[3], False


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
    weights: ScoringWeights | None,
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
    weights: ScoringWeights | None,
    config: TransitionScoringConfig,
    cache: dict[tuple, TransitionScore] | None,
    max_bpm_difference_percent: float | None,
) -> float:
    score = score_transition(
        left, right, weights=weights, boost_rules=boost_rules, cache=cache, config=config
    ).total_score
    if max_bpm_difference_percent is None or left.bpm is None or right.bpm is None or not left.bpm:
        return score
    # Fold 2:1 pairs and use the lower BPM as the symmetric denominator,
    # matching the transition scorer's continuity calculation.
    if bpm_difference_percent(left.bpm, right.bpm) > max_bpm_difference_percent:
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
