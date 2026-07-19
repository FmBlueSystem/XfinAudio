"""Playlist recommendation service combining strategy policy, controls, and sequencing."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from xfinaudio.audio.spectral_profile import ColorName
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import AppliedControls, DJControls, apply_controls
from xfinaudio.recommendation.optimizer import recommend_sequence
from xfinaudio.recommendation.scoring import (
    ScoringWeights,
    TransitionScore,
    TransitionScoringConfig,
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


def recommendation_without_paths(
    recommendation: PlaylistRecommendation,
    removed_paths: frozenset[str],
    *,
    spectral_cohesion: float = 0.0,
) -> PlaylistRecommendation:
    """Return a recommendation with removed tracks and honest adjacency scores."""
    if not removed_paths:
        return recommendation
    ordered_tracks = [track for track in recommendation.ordered_tracks if track.path not in removed_paths]
    if len(ordered_tracks) == len(recommendation.ordered_tracks):
        return recommendation

    scoring_config = TransitionScoringConfig(
        weights=recommendation.strategy.weights,
        spectral_cohesion=spectral_cohesion,
    )
    transition_scores = _score_ordered_tracks(ordered_tracks, scoring_config)
    return recommendation.model_copy(
        update={
            "ordered_tracks": ordered_tracks,
            "transition_scores": transition_scores,
            "total_score": sum(score.total_score for score in transition_scores),
        }
    )


def recommend_playlist(
    tracks: list[TrackRecord],
    strategy_name: StrategyName | str,
    controls: DJControls | None = None,
    weights_override: ScoringWeights | None = None,
    strategy_registry: StrategyRegistry | None = None,
    spectral_cohesion: float = 0.0,
) -> PlaylistRecommendation:
    """Recommend a playlist using a strategy profile and optional DJ controls."""
    strategy = (strategy_registry or default_strategy_registry()).get(str(strategy_name))
    controls = controls or DJControls()
    # Session-scoped transition score cache: created fresh per call, threaded into
    # the optimizer and final scoring so repeated (left, right, weights) pairs are
    # computed once. Never persists between recommend_playlist calls.
    _score_cache: dict[tuple, TransitionScore] = {}
    warnings: list[str] = []
    scoring_config = TransitionScoringConfig(
        weights=weights_override or strategy.weights,
        spectral_cohesion=spectral_cohesion,
    )
    complete_tracks = [track for track in tracks if track.metadata_status == "complete"]
    incomplete_count = len(tracks) - len(complete_tracks)
    if incomplete_count:
        warnings.append(f"Excluded {incomplete_count} incomplete track(s)")

    filtered_tracks, filter_warnings = _apply_strategy_filters(
        complete_tracks, strategy, preserve_paths=_preserved_control_paths(controls)
    )
    warnings.extend(filter_warnings)
    if strategy.name == "same_genre":
        filtered_tracks, genre_warnings = _apply_genre_filter(
            filtered_tracks, controls, preserve_paths=_preserved_control_paths(controls)
        )
        warnings.extend(genre_warnings)
    if strategy.name == "same_color":
        filtered_tracks, color_warnings = _apply_color_filter(
            filtered_tracks, controls, preserve_paths=_preserved_control_paths(controls)
        )
        warnings.extend(color_warnings)
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

    manual_prefix = _manual_prefix_without_terminal_end(applied.manual_prefix, applied.end_path)
    manual_paths = {track.path for track in manual_prefix}
    remaining_tracks = [track for track in applied.candidate_tracks if track.path not in manual_paths]
    start_path = applied.start_path if not manual_prefix else None
    if manual_prefix and applied.start_path not in (None, manual_prefix[0].path):
        warnings.append("start_path ignored because manual order prefix is applied")

    if _vibe_metadata_unavailable(strategy, applied.candidate_tracks):
        warnings.append("same_vibe metadata unavailable; falling back to harmonic sequencing")

    if _uses_strategy_order(strategy):
        # Strategy-order strategies have a single sequencing stage (no separate optimizer
        # pass), so `sequenced_tracks` here already IS the final order — one gate call,
        # seeded with the manual anchor when present, validates the whole thing at once.
        sequenced_tracks = _apply_terminal_constraints(remaining_tracks, start_path, applied.end_path)
        if manual_prefix:
            sequenced_tracks, dropped_bpm_jump_count = _drop_generated_tracks_after_impossible_bpm_jumps(
                [manual_prefix[-1], *sequenced_tracks]
            )
            sequenced_tracks = sequenced_tracks[1:]
        else:
            sequenced_tracks, dropped_bpm_jump_count = _drop_generated_tracks_after_impossible_bpm_jumps(
                sequenced_tracks
            )
        if dropped_bpm_jump_count:
            warnings.append(_bpm_jump_warning(dropped_bpm_jump_count))
        optimizer = "strategy-order"
    else:
        # The optimizer branch has two distinct sequencing stages, so it needs two gate
        # calls: this first one filters the unordered candidate pool BEFORE `recommend_sequence`
        # picks the final adjacency (it never sees manual_prefix — there is no "final order" yet).
        remaining_tracks, dropped_bpm_jump_count = _drop_generated_tracks_after_impossible_bpm_jumps(remaining_tracks)
        if dropped_bpm_jump_count:
            warnings.append(_bpm_jump_warning(dropped_bpm_jump_count))
        sequenced = recommend_sequence(
            remaining_tracks,
            start_path=start_path,
            end_path=applied.end_path,
            weights=scoring_config.weights,
            cache=_score_cache,
            config=scoring_config,
        )
        sequenced_tracks = sequenced.ordered_tracks
        optimizer = sequenced.optimizer
        # Second gate call: now that the true final order is known, re-validate it seeded
        # with the manual anchor. This can drop more than just the manual->generated seam
        # (it walks the whole chain, same as the pre-existing start_path/anchor pattern), so
        # the warning describes the mechanism ("re-validating... anchored on") rather than
        # claiming the manual track specifically caused every drop.
        if manual_prefix:
            seeded, post_sequencing_dropped_count = _drop_generated_tracks_after_impossible_bpm_jumps(
                [manual_prefix[-1], *sequenced_tracks]
            )
            sequenced_tracks = seeded[1:]
            if post_sequencing_dropped_count:
                warnings.append(
                    _bpm_jump_warning(
                        post_sequencing_dropped_count,
                        suffix=" while re-validating the sequence anchored on the manually ordered tracks",
                    )
                )

    ordered_tracks = [*manual_prefix, *sequenced_tracks]
    transition_scores = _score_ordered_tracks(ordered_tracks, scoring_config, cache=_score_cache)
    warnings.extend(_spectral_jump_warnings(ordered_tracks))

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


def _apply_genre_filter(
    tracks: list[TrackRecord], controls: DJControls, preserve_paths: set[str]
) -> tuple[list[TrackRecord], list[str]]:
    anchor_genre = _resolve_anchor_genre(tracks, controls)
    if anchor_genre is None:
        return tracks, []

    warnings = [f"same_genre filter applied: {anchor_genre}"]
    filtered = [track for track in tracks if track.path in preserve_paths or _normalized_genre(track) == anchor_genre]
    eligible = [track for track in filtered if track.path not in preserve_paths]
    if not eligible:
        warnings.append(
            f"same_genre: no candidates match anchor genre '{anchor_genre}'; falling back to unfiltered scoring"
        )
        return tracks, warnings
    return filtered, warnings


def _resolve_anchor_genre(tracks: list[TrackRecord], controls: DJControls) -> str | None:
    by_path = {track.path: track for track in tracks}
    if (
        controls.start_path is not None
        and (start_track := by_path.get(controls.start_path)) is not None
        and (start_genre := _normalized_genre(start_track))
    ):
        return start_genre

    manual_genres = [
        genre
        for path in controls.manual_order_paths
        if path not in controls.excluded_paths and (track := by_path.get(path)) is not None
        if (genre := _normalized_genre(track)) is not None
    ]
    if manual_genres:
        return _dominant_genre(manual_genres)

    for track in tracks:
        if genre := _normalized_genre(track):
            return genre
    return None


def _dominant_genre(genres: list[str]) -> str:
    first_seen: dict[str, int] = {}
    counts: dict[str, int] = {}
    for index, genre in enumerate(genres):
        first_seen.setdefault(genre, index)
        counts[genre] = counts.get(genre, 0) + 1
    return min(counts, key=lambda genre: (-counts[genre], first_seen[genre]))


def _apply_color_filter(
    tracks: list[TrackRecord], controls: DJControls, preserve_paths: set[str]
) -> tuple[list[TrackRecord], list[str]]:
    anchor_color = _resolve_anchor_color(tracks, controls)
    if anchor_color is None:
        return tracks, []

    warnings = [f"same_color filter applied: {anchor_color}"]
    filtered = [track for track in tracks if track.path in preserve_paths or _track_color(track) == anchor_color]
    eligible = [track for track in filtered if track.path not in preserve_paths]
    if not eligible:
        warnings.append(
            f"same_color: no candidates match anchor color '{anchor_color}'; falling back to unfiltered scoring"
        )
        return tracks, warnings
    return filtered, warnings


def _resolve_anchor_color(tracks: list[TrackRecord], controls: DJControls) -> ColorName | None:
    by_path = {track.path: track for track in tracks}
    if (
        controls.start_path is not None
        and (start_track := by_path.get(controls.start_path)) is not None
        and (start_color := _track_color(start_track)) is not None
    ):
        return start_color

    manual_colors: list[ColorName] = [
        color
        for path in controls.manual_order_paths
        if path not in controls.excluded_paths and (manual_track := by_path.get(path)) is not None
        if (color := _track_color(manual_track)) is not None
    ]
    if manual_colors:
        return _dominant_color_value(manual_colors)

    for candidate in tracks:
        if (color := _track_color(candidate)) is not None:
            return color
    return None


def _dominant_color_value(colors: list[ColorName]) -> ColorName:
    first_seen: dict[ColorName, int] = {}
    counts: dict[ColorName, int] = {}
    for index, color in enumerate(colors):
        first_seen.setdefault(color, index)
        counts[color] = counts.get(color, 0) + 1
    return min(counts, key=lambda color: (-counts[color], first_seen[color]))


def _track_color(track: TrackRecord) -> ColorName | None:
    profile = track.spectral_profile
    return None if profile is None else profile.dominant_color


def _normalized_genre(track: TrackRecord) -> str | None:
    if track.genre is None:
        return None
    genre = track.genre.casefold().strip()
    return genre or None


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
    tolerance = strategy.energy_tolerance
    if tolerance is None:
        return candidate_tracks, []
    min_energy = anchor_energy - tolerance
    max_energy = anchor_energy + tolerance
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


def _bpm_jump_warning(dropped_count: int, *, suffix: str = "") -> str:
    return (
        "Dropped "
        f"{dropped_count} generated track(s) because adjacent BPM jump exceeded "
        f"{MAX_ADJACENT_BPM_DIFFERENCE_PERCENT:.1f}%{suffix}"
    )


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


def _score_ordered_tracks(
    tracks: list[TrackRecord],
    config: TransitionScoringConfig,
    cache: dict[tuple, TransitionScore] | None = None,
) -> list[TransitionScore]:
    return [
        score_transition(left, right, weights=config.weights, cache=cache, config=config)
        for left, right in zip(tracks, tracks[1:], strict=False)
    ]


def _spectral_jump_warnings(tracks: list[TrackRecord]) -> list[str]:
    """Summarize adjacent tracks with different dominant spectral colors."""
    shift_counts: dict[tuple[str, str], int] = {}
    for left, right in zip(tracks, tracks[1:], strict=False):
        left_profile = left.spectral_profile
        right_profile = right.spectral_profile
        if left_profile is None or right_profile is None:
            continue
        left_color = left_profile.dominant_color
        right_color = right_profile.dominant_color
        if left_color != right_color:
            key = (left_color, right_color)
            shift_counts[key] = shift_counts.get(key, 0) + 1
    if not shift_counts:
        return []
    summary = ", ".join(
        f"{left}→{right} ({count} {'time' if count == 1 else 'times'})" for (left, right), count in shift_counts.items()
    )
    return [f"Spectral shifts: {summary}"]


__all__ = ["PlaylistRecommendation", "recommend_playlist"]
