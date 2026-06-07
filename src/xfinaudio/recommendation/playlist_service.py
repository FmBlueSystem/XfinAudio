"""Playlist recommendation service combining strategy policy, controls, and sequencing."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import AppliedControls, DJControls, apply_controls
from xfinaudio.recommendation.optimizer import recommend_sequence
from xfinaudio.recommendation.scoring import (
    ScoringWeights,
    TransitionScore,
    _bpm_difference_percent,
    score_transition,
)
from xfinaudio.recommendation.strategies import (
    PlaylistStrategy,
    StrategyName,
    StrategyRegistry,
    default_strategy_registry,
)

MAX_ADJACENT_BPM_DIFFERENCE_PERCENT = 3.0


class PlaylistRecommendation(BaseModel):
    """Product-level playlist recommendation returned to desktop callers."""

    model_config = ConfigDict(frozen=True)

    ordered_tracks: list[TrackRecord]
    transition_scores: list[TransitionScore]
    strategy: PlaylistStrategy
    warnings: list[str]
    applied_controls: dict[str, object]
    optimizer: str
    total_score: float


def recommend_playlist(
    tracks: list[TrackRecord],
    strategy_name: StrategyName | str,
    controls: DJControls | None = None,
    weights_override: ScoringWeights | None = None,
    strategy_registry: StrategyRegistry | None = None,
) -> PlaylistRecommendation:
    """Recommend a playlist using a strategy profile and optional DJ controls."""
    strategy = (strategy_registry or default_strategy_registry()).get(str(strategy_name))
    controls = controls or DJControls()
    warnings: list[str] = []
    complete_tracks = [track for track in tracks if track.metadata_status == "complete"]
    incomplete_count = len(tracks) - len(complete_tracks)
    if incomplete_count:
        warnings.append(f"Excluded {incomplete_count} incomplete track(s)")

    filtered_tracks, filter_warnings = _apply_strategy_filters(
        complete_tracks, strategy, preserve_paths=_preserved_control_paths(controls)
    )
    warnings.extend(filter_warnings)
    applied = apply_controls(filtered_tracks, controls)

    anchor_energy = _resolve_anchor_energy(applied)
    if strategy.energy_tolerance is not None and anchor_energy is not None:
        preserve_paths = _preserved_control_paths(controls)
        tolerance_filtered, tolerance_warnings = _apply_energy_tolerance(
            applied.candidate_tracks, strategy, anchor_energy, preserve_paths
        )
        warnings.extend(tolerance_warnings)
        applied = AppliedControls(
            candidate_tracks=tolerance_filtered,
            manual_prefix=applied.manual_prefix,
            locked_paths=applied.locked_paths,
            excluded_paths=applied.excluded_paths,
            start_path=applied.start_path,
            end_path=applied.end_path,
        )

    weights = weights_override or strategy.weights

    manual_prefix = _manual_prefix_without_terminal_end(applied.manual_prefix, applied.end_path)
    manual_paths = {track.path for track in manual_prefix}
    remaining_tracks = [track for track in applied.candidate_tracks if track.path not in manual_paths]
    start_path = applied.start_path if not manual_prefix else None
    if manual_prefix and applied.start_path not in (None, manual_prefix[0].path):
        warnings.append("start_path ignored because manual order prefix is applied")

    if _vibe_metadata_unavailable(strategy, applied.candidate_tracks):
        warnings.append("same_vibe metadata unavailable; falling back to harmonic sequencing")

    if _uses_strategy_order(strategy):
        sequenced_tracks = _apply_terminal_constraints(remaining_tracks, start_path, applied.end_path)
        optimizer = "strategy-order"
    else:
        sequenced = recommend_sequence(
            remaining_tracks,
            start_path=start_path,
            end_path=applied.end_path,
            weights=weights,
        )
        sequenced_tracks = sequenced.ordered_tracks
        optimizer = sequenced.optimizer

    ordered_tracks = [*manual_prefix, *sequenced_tracks]
    ordered_tracks, dropped_bpm_jump_count = _drop_generated_tracks_after_impossible_bpm_jumps(ordered_tracks)
    if dropped_bpm_jump_count:
        warnings.append(
            "Dropped "
            f"{dropped_bpm_jump_count} generated track(s) because adjacent BPM jump exceeded "
            f"{MAX_ADJACENT_BPM_DIFFERENCE_PERCENT:.1f}%"
        )
    transition_scores = _score_ordered_tracks(ordered_tracks, weights)

    return PlaylistRecommendation(
        ordered_tracks=ordered_tracks,
        transition_scores=transition_scores,
        strategy=strategy,
        warnings=warnings,
        applied_controls=applied.summary(),
        optimizer=optimizer,
        total_score=sum(score.total_score for score in transition_scores),
    )


def _manual_prefix_without_terminal_end(manual_prefix: list[TrackRecord], end_path: str | None) -> list[TrackRecord]:
    if end_path is None:
        return manual_prefix
    return [track for track in manual_prefix if track.path != end_path]


def _uses_strategy_order(strategy: PlaylistStrategy) -> bool:
    return strategy.sort_hint in {"energy_ascending", "energy_descending", "bpm_ascending"}


def _apply_terminal_constraints(
    tracks: list[TrackRecord], start_path: str | None, end_path: str | None
) -> list[TrackRecord]:
    ordered = list(tracks)
    if start_path is not None:
        ordered = _move_path_to_edge(ordered, start_path, first=True)
    if end_path is not None:
        ordered = _move_path_to_edge(ordered, end_path, first=False)
    return ordered


def _move_path_to_edge(tracks: list[TrackRecord], path: str, *, first: bool) -> list[TrackRecord]:
    matching = [track for track in tracks if track.path == path]
    if not matching:
        return tracks
    others = [track for track in tracks if track.path != path]
    return [*matching, *others] if first else [*others, *matching]


def _apply_strategy_filters(
    tracks: list[TrackRecord], strategy: PlaylistStrategy, preserve_paths: set[str]
) -> tuple[list[TrackRecord], list[str]]:
    filtered = tracks
    warnings: list[str] = []
    if strategy.energy_range is not None:
        low, high = strategy.energy_range
        filtered = [
            track
            for track in filtered
            if track.path in preserve_paths or (track.energy_level is not None and low <= track.energy_level <= high)
        ]
        removed = len(tracks) - len(filtered)
        if removed:
            warnings.append(f"Filtered {removed} track(s) outside {strategy.name} energy range")
    if strategy.bpm_range is not None:
        low, high = strategy.bpm_range
        before = len(filtered)
        filtered = [
            track
            for track in filtered
            if track.path in preserve_paths or (track.bpm is not None and low <= track.bpm <= high)
        ]
        removed = before - len(filtered)
        if removed:
            warnings.append(f"Filtered {removed} track(s) outside {strategy.name} BPM range")
    return _sort_by_hint(filtered, strategy), warnings


def _preserved_control_paths(controls: DJControls) -> set[str]:
    preserved = set(controls.locked_paths) | set(controls.manual_order_paths)
    if controls.start_path is not None:
        preserved.add(controls.start_path)
    if controls.end_path is not None:
        preserved.add(controls.end_path)
    return preserved - controls.excluded_paths


def _resolve_anchor_energy(applied: AppliedControls) -> int | None:
    if applied.start_path is not None:
        for track in applied.candidate_tracks:
            if track.path == applied.start_path and track.energy_level is not None:
                return track.energy_level
    for track in applied.manual_prefix:
        if track.energy_level is not None:
            return track.energy_level
    for track in applied.candidate_tracks:
        if track.energy_level is not None:
            return track.energy_level
    return None


def _apply_energy_tolerance(
    candidate_tracks: list[TrackRecord],
    strategy: PlaylistStrategy,
    anchor_energy: int,
    preserve_paths: set[str],
) -> tuple[list[TrackRecord], list[str]]:
    min_energy = anchor_energy - strategy.energy_tolerance
    max_energy = anchor_energy + strategy.energy_tolerance
    filtered = [
        track
        for track in candidate_tracks
        if track.path in preserve_paths
        or (track.energy_level is not None and min_energy <= track.energy_level <= max_energy)
    ]
    removed = len(candidate_tracks) - len(filtered)
    warnings: list[str] = []
    if removed:
        warnings.append(f"Filtered {removed} track(s) outside same_energy energy tolerance")
    return filtered, warnings


def _sort_by_hint(tracks: list[TrackRecord], strategy: PlaylistStrategy) -> list[TrackRecord]:
    if strategy.sort_hint == "energy_ascending":
        return sorted(
            tracks,
            key=lambda track: (
                track.energy_level is None,
                track.energy_level or 0,
                track.bpm is None,
                track.bpm or 0.0,
                track.path,
            ),
        )
    if strategy.sort_hint == "energy_descending":
        return sorted(
            tracks,
            key=lambda track: (
                track.energy_level is None,
                -(track.energy_level or 0),
                track.bpm is None,
                track.bpm or 0.0,
                track.path,
            ),
        )
    if strategy.sort_hint == "bpm_ascending":
        return sorted(tracks, key=lambda track: (track.bpm is None, track.bpm or 0.0, track.path))
    return sorted(tracks, key=lambda track: track.path)


def _drop_generated_tracks_after_impossible_bpm_jumps(
    tracks: list[TrackRecord], *, max_bpm_difference_percent: float = MAX_ADJACENT_BPM_DIFFERENCE_PERCENT
) -> tuple[list[TrackRecord], int]:
    if len(tracks) < 2:
        return tracks, 0

    kept = [tracks[0]]
    dropped_count = 0
    for candidate in tracks[1:]:
        if candidate.bpm is None or kept[-1].bpm is None:
            kept.append(candidate)
            continue
        if _bpm_difference_percent(kept[-1].bpm, candidate.bpm) > max_bpm_difference_percent:
            dropped_count += 1
            continue
        kept.append(candidate)
    return kept, dropped_count


def _vibe_metadata_unavailable(strategy: PlaylistStrategy, tracks: list[TrackRecord]) -> bool:
    if not (strategy.requires_vibe_metadata and strategy.degrade_without_vibe_metadata):
        return False
    return all(not track.genre and not track.tags for track in tracks)


def _score_ordered_tracks(tracks: list[TrackRecord], weights: ScoringWeights) -> list[TransitionScore]:
    return [score_transition(left, right, weights=weights) for left, right in zip(tracks, tracks[1:], strict=False)]


__all__ = ["PlaylistRecommendation", "recommend_playlist"]
