"""Playlist recommendation service combining strategy policy, controls, and sequencing."""

from __future__ import annotations

import contextlib

from pydantic import BaseModel, ConfigDict

from xfinaudio.audio.spectral_profile import ColorName
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import AppliedControls, DJControls, apply_controls, preserved_control_paths
from xfinaudio.recommendation.energy_arc import traces_an_arc
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
# How many candidates the optimizer gets per slot it will fill. The set is ~15
# tracks; handing the sequencer 120 and trimming the result to 15 is the wrong
# shape of work, and it is what made a set cost seconds. Cost climbs far faster
# than quality -- measured per set: 0.035s at 30 candidates, 0.305s at 60,
# 1.65s at 90, 4.76s at 120, for mean transition scores of 0.814, 0.863, 0.883,
# 0.894. Four per slot buys the shape without the bill.
_SEQUENCING_CANDIDATES_PER_SLOT = 4
_MIN_SEQUENCING_CANDIDATES = 30
# Used when the caller names no set length. `prep_copilot` is the one that does
# this, and it sequences three variants for the DJ to skim rather than one set
# to play, so it is bought at the cheap end of the cost curve: 0.035s per
# sequence against 0.305s at 60, for 0.814 mean transition quality against
# 0.863.
_UNBOUNDED_SEQUENCING_CANDIDATES = 30
_COLOR_FILTER_STRATEGIES: frozenset[str] = frozenset({"same_color", "same_color_energy"})


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


def recommendation_reordered(
    recommendation: PlaylistRecommendation,
    ordered_paths: list[str],
    *,
    spectral_cohesion: float = 0.0,
) -> PlaylistRecommendation:
    """Return a recommendation following *ordered_paths*, with honest adjacency scores.

    The DJ can move tracks by hand before exporting, and the order they leave
    behind is what gets written to the crate. Carrying the optimizer's original
    scores forward would show seams that no longer exist, so every adjacency is
    rescored against the new order.

    *ordered_paths* must be a permutation of the current tracks. Anything else
    is a caller bug -- honouring it would silently drop or invent tracks, and
    the exported crate would not match what the screen showed -- so the
    recommendation is returned unchanged. Removal has its own operation,
    `recommendation_without_paths`.
    """
    current = [track.path for track in recommendation.ordered_tracks]
    if ordered_paths == current:
        return recommendation
    if sorted(ordered_paths) != sorted(current):
        return recommendation

    by_path = {track.path: track for track in recommendation.ordered_tracks}
    ordered_tracks = [by_path[path] for path in ordered_paths]
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


def recommendation_with_replacement(
    recommendation: PlaylistRecommendation,
    removed_path: str,
    candidates: list[TrackRecord],
    *,
    spectral_cohesion: float = 0.0,
) -> PlaylistRecommendation:
    """Replace a removed track with the best-fitting candidate at the same slot.

    The candidate maximizing the summed transition score against the slot's
    neighbors wins; adjacency scores are recomputed for the whole order. Falls
    back to plain removal when no candidate is eligible.
    """
    paths = [item.path for item in recommendation.ordered_tracks]
    if removed_path not in paths:
        return recommendation

    playlist_paths = set(paths)
    eligible = [
        candidate
        for candidate in candidates
        if candidate.path not in playlist_paths and candidate.metadata_status == "complete"
    ]
    if not eligible:
        return recommendation_without_paths(
            recommendation, frozenset({removed_path}), spectral_cohesion=spectral_cohesion
        )

    scoring_config = TransitionScoringConfig(
        weights=recommendation.strategy.weights,
        spectral_cohesion=spectral_cohesion,
    )
    index = paths.index(removed_path)
    left = recommendation.ordered_tracks[index - 1] if index > 0 else None
    right = recommendation.ordered_tracks[index + 1] if index + 1 < len(paths) else None

    def _slot_fit(candidate: TrackRecord) -> float:
        fit = 0.0
        if left is not None:
            fit += score_transition(left, candidate, weights=scoring_config.weights, config=scoring_config).total_score
        if right is not None:
            fit += score_transition(candidate, right, weights=scoring_config.weights, config=scoring_config).total_score
        return fit

    replacement = max(eligible, key=_slot_fit)
    remaining = [item for item in recommendation.ordered_tracks if item.path != removed_path]
    ordered_tracks = [*remaining[:index], replacement, *remaining[index:]]
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
    target_count: int | None = None,
    target_duration_minutes: float | None = None,
    played_seconds_per_track: float | None = None,
) -> PlaylistRecommendation:
    """Recommend a playlist using a strategy profile and optional DJ controls.

    ``target_count`` caps how many tracks the DJ actually plays, which is a
    different question from how many candidates the optimizer gets to choose
    among. Passing a wider pool with a smaller target lets it select rather than
    merely permute: on a real library, a pool of 50 trimmed to 10 scored 0.9002
    against 0.8716 for a pool of 10. ``None`` leaves the result untrimmed, but
    the optimizer is still handed a bounded shortlist -- sequencing every
    candidate costs far more than it returns.

    ``target_duration_minutes`` expresses the same cap the way a booked DJ
    actually knows it -- a slot length -- and wins over ``target_count`` when
    both are given. A fixed count cannot hit a slot: 10 tracks ran anywhere from
    36 to 71 minutes on a real library.

    ``played_seconds_per_track`` is how long each track is actually on air before
    the mix moves on. A DJ plays a segment, not the whole record, so summing full
    durations answers "how long is this music" rather than "how long is my set".
    ``None`` counts each track in full.
    """
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
        complete_tracks, strategy, preserve_paths=preserved_control_paths(controls)
    )
    warnings.extend(filter_warnings)
    # The DJ's explicit choice comes first; `same_genre` still infers one from
    # the anchor when nothing was asked for.
    filtered_tracks, requested_genre_warnings = _apply_requested_genre(
        filtered_tracks, controls.genre if controls is not None else None, preserved_control_paths(controls)
    )
    warnings.extend(requested_genre_warnings)
    if strategy.name == "same_genre" and not (controls is not None and controls.genre):
        filtered_tracks, genre_warnings = _apply_genre_filter(
            filtered_tracks, controls, preserve_paths=preserved_control_paths(controls)
        )
        warnings.extend(genre_warnings)
    if strategy.name in _COLOR_FILTER_STRATEGIES:
        filtered_tracks, color_warnings = _apply_color_filter(
            filtered_tracks, controls, preserve_paths=preserved_control_paths(controls), strategy_name=strategy.name
        )
        warnings.extend(color_warnings)
    applied = apply_controls(filtered_tracks, controls)

    anchor_energy = _resolve_anchor_energy(applied)
    if strategy.energy_tolerance is not None and anchor_energy is not None:
        preserve_paths = preserved_control_paths(controls)
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
        # Shield the control tracks: this gate runs on an unordered pool, so the
        # anchor is not necessarily first, and recommend_sequence below rejects
        # the request outright if start_path is missing from what it receives.
        remaining_tracks, dropped_bpm_jump_count = _bpm_reachable_from(
            remaining_tracks, start_path, preserve_paths=preserved_control_paths(controls)
        )
        remaining_tracks = _shortlist_for_sequencing(
            remaining_tracks,
            _expected_set_length(remaining_tracks, target_duration_minutes, played_seconds_per_track, target_count),
            preserve_paths=preserved_control_paths(controls),
        )
        if dropped_bpm_jump_count:
            warnings.append(_bpm_jump_warning(dropped_bpm_jump_count))
        sequenced = recommend_sequence(
            remaining_tracks,
            start_path=start_path,
            end_path=applied.end_path,
            weights=scoring_config.weights,
            cache=_score_cache,
            config=scoring_config,
            arc_strategy=strategy.name,
            # A tempo jump the DJ cannot beatmatch is not a bad option, it is not
            # an option -- the sequencer routes around it instead of pricing it.
            max_bpm_difference_percent=MAX_ADJACENT_BPM_DIFFERENCE_PERCENT,
            # The shape must span the set the DJ plays, not the pool it is drawn
            # from. Sizing it by the pool showed only the opening fraction of the
            # curve, so a warm-up never climbed and a journey's peak sat past the
            # end of the set.
            arc_length=_expected_set_length(
                remaining_tracks, target_duration_minutes, played_seconds_per_track, target_count
            ),
        )
        sequenced_tracks = sequenced.ordered_tracks
        optimizer = sequenced.optimizer
        # The sequencer orders everything it is handed, so a track with no
        # playable neighbour still comes back -- parked at an edge, where the
        # penalty is cheapest. Cut those loose now that the true order is known.
        sequenced_tracks, unplayable_count = _drop_generated_tracks_after_impossible_bpm_jumps(
            sequenced_tracks, preserve_paths=preserved_control_paths(controls)
        )
        if unplayable_count:
            dropped_bpm_jump_count += unplayable_count
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
    # Trim after sequencing, not before: the optimizer needs the whole pool to
    # choose good adjacencies, and the DJ only plays the front of the result.
    if target_duration_minutes is not None:
        ordered_tracks = _trim_to_duration(
            ordered_tracks, target_duration_minutes, played_seconds_per_track=played_seconds_per_track
        )
    elif target_count is not None and len(ordered_tracks) > target_count:
        ordered_tracks = ordered_tracks[:target_count]

    # "Genre locked to 'Classical'" is true and useless on its own when the DJ
    # asked for thirty minutes and got four. Some genres are simply too small a
    # corner of the library to fill a slot, and that is worth saying out loud.
    requested_genre = controls.genre if controls is not None else None
    expected = _expected_set_length(ordered_tracks, target_duration_minutes, played_seconds_per_track, target_count)
    if requested_genre and expected is not None and len(ordered_tracks) < expected:
        warnings.append(
            f"Genre '{requested_genre.strip()}' left the set short: "
            f"{len(ordered_tracks)} track(s) for a slot that wants about {expected}"
        )
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


def _trim_to_duration(
    tracks: list[TrackRecord],
    target_minutes: float,
    *,
    played_seconds_per_track: float | None = None,
) -> list[TrackRecord]:
    """Keep tracks from the front until the set covers the booked slot.

    A booked DJ knows their slot in minutes, not in track count. A fixed count of
    10 produced sets between 36 and 71 minutes on a real library, because track
    lengths vary by nearly a factor of two.

    ``played_seconds_per_track`` is how long each track is on air before the mix
    moves on, since a DJ plays a segment rather than the whole record. A track
    shorter than that segment only contributes its own length -- you cannot play
    two minutes of a ninety-second edit. ``None`` counts each track in full.

    The last track is included when it starts before the slot ends, so the set
    covers the slot rather than falling short of it.
    """
    target_seconds = target_minutes * 60
    kept: list[TrackRecord] = []
    elapsed = 0.0
    for candidate in tracks:
        if elapsed >= target_seconds:
            break
        kept.append(candidate)
        length = candidate.duration or 0.0
        elapsed += min(length, played_seconds_per_track) if played_seconds_per_track else length
    return kept


def _manual_prefix_without_terminal_end(manual_prefix: list[TrackRecord], end_path: str | None) -> list[TrackRecord]:
    if end_path is None:
        return manual_prefix
    return [track for track in manual_prefix if track.path != end_path]


def _shortlist_for_sequencing(
    tracks: list[TrackRecord],
    set_length: int | None,
    *,
    preserve_paths: set[str] | None = None,
) -> list[TrackRecord]:
    """Cap what the optimizer sequences at a few candidates per slot it will fill.

    The pool arrives interleaved by energy, so taking the front of it keeps the
    spread a shape needs while cutting the sequencing cost, which climbs far
    faster than the quality it buys. Control tracks are kept whatever the cap.

    A caller that names no set length still gets a cap. `prep_copilot` is one:
    it sequences three variants off the full pool, so leaving it uncapped cost
    three times the full sequencing bill for a plan the DJ skims.
    """
    limit = (
        _UNBOUNDED_SEQUENCING_CANDIDATES
        if set_length is None
        else max(_MIN_SEQUENCING_CANDIDATES, set_length * _SEQUENCING_CANDIDATES_PER_SLOT)
    )
    if len(tracks) <= limit:
        return tracks
    protected = preserve_paths or set()
    kept = [item for item in tracks if item.path in protected]
    for item in tracks:
        if len(kept) >= limit:
            break
        if item.path not in protected:
            kept.append(item)
    return kept


def _expected_set_length(
    candidates: list[TrackRecord],
    target_duration_minutes: float | None,
    played_seconds_per_track: float | None,
    target_count: int | None,
) -> int | None:
    """Return how many tracks the DJ will actually play, if the caller said.

    ``None`` when the caller asked for no cap, which leaves the shape spanning
    the whole sequence -- there is nothing to trim it down to.

    With no ``played_seconds_per_track`` each track counts its own length, so
    the estimate uses the candidates' mean duration. It only has to be close:
    it sizes a curve, and being a track or two out moves every target by a few
    percent.
    """
    if target_duration_minutes is None:
        return target_count
    seconds = played_seconds_per_track
    if seconds is None:
        durations = [track.duration for track in candidates if track.duration]
        seconds = sum(durations) / len(durations) if durations else None
    if not seconds:
        return target_count
    return max(1, round(target_duration_minutes * 60 / seconds))


def _uses_strategy_order(strategy: PlaylistStrategy) -> bool:
    if traces_an_arc(strategy.name):
        return False
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


def _apply_requested_genre(
    tracks: list[TrackRecord], requested: str | None, preserve_paths: set[str]
) -> tuple[list[TrackRecord], list[str]]:
    """Keep only the requested genre, or say why the request could not be met.

    Independent of the strategy on purpose: the shape of a set and the corner of
    the library it is drawn from are separate choices, and coupling them meant
    a genre-locked set had to give up its energy arc.

    An unmatchable genre falls back to the unfiltered pool rather than returning
    nothing -- some genres are simply too small to fill a slot, and a set the DJ
    can edit beats an empty screen.
    """
    wanted = (requested or "").strip().casefold()
    if not wanted:
        return tracks, []
    eligible = [track for track in tracks if _normalized_genre(track) == wanted]
    if not eligible:
        return tracks, [f"No candidates in genre '{requested.strip()}'; showing every genre instead"]
    kept = [track for track in tracks if track.path in preserve_paths or _normalized_genre(track) == wanted]
    return kept, [f"Genre locked to '{requested.strip()}'"]


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


def prefilter_strategy_candidates(
    tracks: list[TrackRecord],
    strategy_name: StrategyName | str,
    controls: DJControls | None = None,
    strategy_registry: StrategyRegistry | None = None,
) -> list[TrackRecord]:
    """Apply a strategy's hard filters to a full candidate pool before interactive capping.

    Interactive adapters truncate the candidate pool for optimizer speed; running
    the same hard filters ``recommend_playlist`` applies (energy/BPM ranges, anchor
    genre, anchor color, energy tolerance) BEFORE that truncation keeps the capped
    pool full of strategy-viable tracks instead of arbitrary scan-order ones.
    """
    strategy = (strategy_registry or default_strategy_registry()).get(str(strategy_name))
    controls = controls or DJControls()
    preserve_paths = preserved_control_paths(controls)
    complete_tracks = [track for track in tracks if track.metadata_status == "complete"]

    filtered, _ = _apply_strategy_filters(complete_tracks, strategy, preserve_paths=preserve_paths)
    # Before the interactive cap, or the 120 slots fill with genres the set will
    # then filter away, leaving a handful of candidates to sequence.
    filtered, _ = _apply_requested_genre(filtered, controls.genre, preserve_paths)
    if strategy.name == "same_genre" and not controls.genre:
        filtered, _ = _apply_genre_filter(filtered, controls, preserve_paths=preserve_paths)
    if strategy.name in _COLOR_FILTER_STRATEGIES:
        filtered, _ = _apply_color_filter(
            filtered, controls, preserve_paths=preserve_paths, strategy_name=strategy.name
        )
    if strategy.energy_tolerance is not None:
        # apply_controls re-validates control paths; a control track filtered out
        # upstream would raise here, so fall back to skipping the tolerance
        # prefilter and let recommend_playlist surface the real error.
        with contextlib.suppress(ValueError):
            applied = apply_controls(filtered, controls)
            anchor_energy = _resolve_anchor_energy(applied)
            if anchor_energy is not None:
                filtered, _ = _apply_energy_tolerance(applied.candidate_tracks, strategy, anchor_energy, preserve_paths)
    return filtered


def _apply_color_filter(
    tracks: list[TrackRecord], controls: DJControls, preserve_paths: set[str], strategy_name: str
) -> tuple[list[TrackRecord], list[str]]:
    anchor_color = _resolve_anchor_color(tracks, controls)
    if anchor_color is None:
        return tracks, []

    warnings = [f"{strategy_name} filter applied: {anchor_color}"]
    filtered = [track for track in tracks if track.path in preserve_paths or _track_color(track) == anchor_color]
    eligible = [track for track in filtered if track.path not in preserve_paths]
    if not eligible:
        warnings.append(
            f"{strategy_name}: no candidates match anchor color '{anchor_color}'; falling back to unfiltered scoring"
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
        warnings.append(f"Filtered {removed} track(s) outside {strategy.name} energy tolerance")
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


def _bpm_reachable_from(
    tracks: list[TrackRecord],
    anchor_path: str | None,
    *,
    max_bpm_difference_percent: float = MAX_ADJACENT_BPM_DIFFERENCE_PERCENT,
    preserve_paths: set[str] | None = None,
) -> tuple[list[TrackRecord], int]:
    """Keep the candidates a set can actually reach from the anchor."""
    protected = set(preserve_paths or set())
    if anchor_path is not None:
        protected.add(anchor_path)
    passthrough = [item for item in tracks if item.bpm is None or item.path in protected]
    measurable = sorted(
        (item for item in tracks if item.bpm is not None and item.path not in protected),
        key=lambda item: (item.bpm or 0.0, item.path),
    )
    if not measurable:
        return tracks, 0
    anchor = next((item for item in tracks if item.path == anchor_path), None)
    anchored = anchor is not None and anchor.bpm is not None
    line = sorted(
        [*measurable, anchor] if anchored and anchor is not None else measurable,
        key=lambda item: (item.bpm or 0.0, item.path),
    )
    runs: list[list[TrackRecord]] = [[line[0]]]
    for previous, current in zip(line, line[1:], strict=False):
        if _bpm_difference_percent(previous.bpm or 0.0, current.bpm or 0.0) > max_bpm_difference_percent:
            runs.append([current])
        else:
            runs[-1].append(current)
    chosen: list[TrackRecord] | None = None
    if anchored:
        chosen = next((run for run in runs if any(item.path == anchor_path for item in run)), None)
    if chosen is None:
        chosen = max(runs, key=len)
    reachable = {item.path for item in chosen}
    kept = [item for item in tracks if item.path in reachable or item in passthrough]
    return kept, len(tracks) - len(kept)


def _drop_generated_tracks_after_impossible_bpm_jumps(
    tracks: list[TrackRecord],
    *,
    max_bpm_difference_percent: float = MAX_ADJACENT_BPM_DIFFERENCE_PERCENT,
    preserve_paths: set[str] | None = None,
) -> tuple[list[TrackRecord], int]:
    """Drop tracks whose BPM jump from the last kept one is unplayable.

    ``preserve_paths`` shields the DJ's control tracks, as every other filter in
    this module already does. Without it the anchor could be dropped here and
    ``recommend_sequence`` would then reject the whole request with "Unknown
    start_path" -- the gate walks the list in order and compares against the last
    kept track, so whether the anchor survived depended on candidate ordering.
    """
    if len(tracks) < 2:
        return tracks, 0

    protected = preserve_paths or set()
    kept = [tracks[0]]
    dropped_count = 0
    for candidate in tracks[1:]:
        if candidate.path in protected:
            kept.append(candidate)
            continue
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


__all__ = [
    "PlaylistRecommendation",
    "prefilter_strategy_candidates",
    "recommend_playlist",
    "recommendation_with_replacement",
    "recommendation_reordered",
    "recommendation_without_paths",
]
