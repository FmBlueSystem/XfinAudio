"""Explainable playlist recommendation reports."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class TrackExplanation(BaseModel):
    """Track identity used in explanation reports."""

    model_config = ConfigDict(frozen=True)

    path: str
    title: str | None = None
    artist: str | None = None
    bpm: float | None = None
    camelot_key: str | None = None
    energy_level: int | None = None
    metadata_status: str


class TransitionExplanation(BaseModel):
    """Human-readable and machine-readable transition explanation."""

    model_config = ConfigDict(frozen=True)

    order: int
    left: TrackExplanation
    right: TrackExplanation
    key_score: float | None = None
    bpm_score: float | None = None
    energy_score: float | None = None
    tag_score: float | None = None
    component_scores: dict[str, float]
    final_score: float
    warnings: list[str]
    explanations: list[str]


class PlaylistExplanation(BaseModel):
    """Explainability report for a playlist recommendation."""

    model_config = ConfigDict(frozen=True)

    strategy: str
    optimizer: str
    track_count: int
    transition_count: int
    total_score: float
    warnings: list[str]
    transitions: list[TransitionExplanation]


def build_playlist_explanation(recommendation: PlaylistRecommendation) -> PlaylistExplanation:
    """Build a deterministic explainability report from a recommendation."""
    tracks_by_path = {track.path: track for track in recommendation.ordered_tracks}
    transitions = []
    for index, transition_score in enumerate(recommendation.transition_scores, start=1):
        component_scores = dict(sorted(transition_score.component_scores.items()))
        transitions.append(
            TransitionExplanation(
                order=index,
                left=_track_explanation(tracks_by_path[transition_score.left_path]),
                right=_track_explanation(tracks_by_path[transition_score.right_path]),
                key_score=component_scores.get("harmonic"),
                bpm_score=component_scores.get("bpm"),
                energy_score=component_scores.get("energy"),
                tag_score=component_scores.get("tags"),
                component_scores=component_scores,
                final_score=transition_score.total_score,
                warnings=list(transition_score.warnings),
                explanations=list(transition_score.explanations),
            )
        )
    return PlaylistExplanation(
        strategy=recommendation.strategy.name,
        optimizer=recommendation.optimizer,
        track_count=len(recommendation.ordered_tracks),
        transition_count=len(recommendation.transition_scores),
        total_score=recommendation.total_score,
        warnings=list(recommendation.warnings),
        transitions=transitions,
    )


def _track_explanation(track: TrackRecord) -> TrackExplanation:
    return TrackExplanation(
        path=track.path,
        title=track.title,
        artist=track.artist,
        bpm=track.bpm,
        camelot_key=track.camelot_key,
        energy_level=track.energy_level,
        metadata_status=track.metadata_status,
    )


__all__ = ["PlaylistExplanation", "TrackExplanation", "TransitionExplanation", "build_playlist_explanation"]
