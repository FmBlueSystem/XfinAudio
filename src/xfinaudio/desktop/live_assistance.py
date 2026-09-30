"""Fail-closed, offline Live suggestions from the exact applied engine set."""

from __future__ import annotations

from dataclasses import dataclass

from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport, build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import TransitionScore, TransitionScoringConfig, score_transition


@dataclass(frozen=True)
class LiveCandidate:
    track: TrackRecord
    score: TransitionScore
    readiness: DjReadinessReport


def _controls_allow(
    recommendation: PlaylistRecommendation,
    paths: list[str],
    locked_paths: frozenset[str],
    excluded_paths: frozenset[str],
) -> bool:
    try:
        controls = DJControls.model_validate(recommendation.applied_controls)
    except ValueError:
        return False
    known = set(paths)
    if not paths or len(known) != len(paths) or "" in known:
        return False
    if known & (excluded_paths | controls.excluded_paths):
        return False
    if not (locked_paths | controls.locked_paths) <= known:
        return False
    if controls.start_path is not None and paths[0] != controls.start_path:
        return False
    if controls.end_path is not None and paths[-1] != controls.end_path:
        return False
    manual = [path for path in controls.manual_order_paths if path not in controls.excluded_paths]
    return paths[: len(manual)] == manual


def _rescore(
    recommendation: PlaylistRecommendation, paths: list[str], spectral_cohesion: float
) -> tuple[PlaylistRecommendation, DjReadinessReport]:
    by_path = {track.path: track for track in recommendation.ordered_tracks}
    tracks = [by_path[path] for path in paths]
    config = TransitionScoringConfig(weights=recommendation.strategy.weights, spectral_cohesion=spectral_cohesion)
    scores = [score_transition(left, right, config=config) for left, right in zip(tracks, tracks[1:], strict=False)]
    measured = recommendation.model_copy(
        update={
            "ordered_tracks": tracks,
            "transition_scores": scores,
            "total_score": sum(s.total_score for s in scores),
        }
    )
    return measured, build_dj_readiness_report(measured, build_quality_report(measured))


def live_session_ready(
    recommendation: PlaylistRecommendation | None,
    readiness: DjReadinessReport | None,
    *,
    locked_paths: frozenset[str] = frozenset(),
    excluded_paths: frozenset[str] = frozenset(),
    spectral_cohesion: float = 0.0,
) -> bool:
    """Require applied readiness and fresh local validation; never trust a stale badge."""
    if recommendation is None or readiness is None or readiness.status != "ready":
        return False
    if readiness.blocker_count or readiness.review_count or any(check.status != "ready" for check in readiness.checks):
        return False
    paths = [track.path for track in recommendation.ordered_tracks]
    if len(paths) < 2 or not _controls_allow(recommendation, paths, locked_paths, excluded_paths):
        return False
    _, measured = _rescore(recommendation, paths, spectral_cohesion)
    return measured.status == "ready"


def rank_live_candidates(
    recommendation: PlaylistRecommendation,
    played_paths: tuple[str, ...],
    *,
    locked_paths: frozenset[str] = frozenset(),
    excluded_paths: frozenset[str] = frozenset(),
    spectral_cohesion: float = 0.0,
) -> list[LiveCandidate]:
    """Rank next choices only when the complete resulting order remains ready.

    Every track remains in the applied pool, so generation-time genre, colour and
    loudness gates cannot be widened. Locks remain present; start/end/manual order
    constrain the proposed permutation. Arc-shaped sets keep their original order.
    """
    paths = [track.path for track in recommendation.ordered_tracks]
    if not played_paths or len(set(played_paths)) != len(played_paths) or not set(played_paths) <= set(paths):
        return []
    if not _controls_allow(recommendation, paths, locked_paths, excluded_paths):
        return []
    remaining = [path for path in paths if path not in played_paths]
    ranked = []
    preserve_order = recommendation.strategy.name in {"warmup", "build", "peak_time", "chill"}
    for candidate in remaining[:1] if preserve_order else remaining:
        proposed = [*played_paths, candidate, *(path for path in remaining if path != candidate)]
        if not _controls_allow(recommendation, proposed, locked_paths, excluded_paths):
            continue
        measured, readiness = _rescore(recommendation, proposed, spectral_cohesion)
        if readiness.status != "ready":
            continue
        index = len(played_paths)
        ranked.append(LiveCandidate(measured.ordered_tracks[index], measured.transition_scores[index - 1], readiness))
    return sorted(ranked, key=lambda item: (-item.score.total_score, item.track.path))
