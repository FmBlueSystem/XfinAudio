"""Evaluate a proposed saved-set order with the existing musical engine."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from xfinaudio.application.playlist_edit_intents import validate_edit
from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.tempo import is_valid_bpm
from xfinaudio.quality.dj_readiness import DjReadinessReport, build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport, build_quality_report
from xfinaudio.recommendation.camelot import parse_camelot_key
from xfinaudio.recommendation.controls import DJControls, apply_controls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import TransitionScoringConfig, score_transition
from xfinaudio.recommendation.strategies import default_strategy_registry


@dataclass(frozen=True)
class PlaylistEditAssessment:
    recommendation: PlaylistRecommendation
    quality: RecommendationQualityReport
    readiness: DjReadinessReport
    description: str


def assess_playlist_edit(
    paths: Sequence[str],
    records: Sequence[TrackRecord],
    *,
    locked_paths: Collection[str] = (),
    excluded_paths: Collection[str] = (),
) -> PlaylistEditAssessment:
    """Score the exact order, reject hard blockers, and retain review warnings."""
    validate_edit(paths, paths, locked_paths=locked_paths, excluded_paths=excluded_paths)
    by_path = {record.path: record for record in records}
    if any(path not in by_path for path in paths):
        raise ValueError("Scan this saved set first: real track metadata is required for musical validation.")
    tracks = [by_path[path] for path in paths]
    for track in tracks:
        if not is_valid_bpm(track.bpm) or track.energy_level is None or not 1 <= track.energy_level <= 10:
            raise ValueError("Repair missing or invalid BPM/energy metadata before applying conversational edits.")
        try:
            parse_camelot_key(track.camelot_key or "")
        except ValueError as error:
            raise ValueError(
                "Repair missing or invalid Camelot key metadata before applying conversational edits."
            ) from error
    applied = apply_controls(
        tracks,
        DJControls(
            locked_paths=set(locked_paths) & set(paths),
            excluded_paths=set(excluded_paths),
        ),
    )
    strategy = default_strategy_registry().get("build")
    config = TransitionScoringConfig(weights=strategy.weights)
    scores = [score_transition(left, right, config=config) for left, right in zip(tracks, tracks[1:], strict=False)]
    recommendation = PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=scores,
        strategy=strategy,
        warnings=[],
        applied_controls=applied.summary(),
        optimizer="offline-editor-validation",
        total_score=sum(score.total_score for score in scores),
    )
    quality = build_quality_report(recommendation)
    readiness = build_dj_readiness_report(recommendation, quality)
    if readiness.status == "blocked":
        raise ValueError("; ".join(check.detail for check in readiness.checks if check.status == "blocked"))
    description = "\n".join(
        [
            f"Engine validation (build strategy): {readiness.summary}",
            f"Mean transition score: {quality.average_transition_score:.3f}",
            *(f"{check.label}: {check.detail}" for check in readiness.checks if check.status != "ready"),
            *(warning for score in scores for warning in score.warnings),
        ]
    )
    return PlaylistEditAssessment(recommendation, quality, readiness, description)
