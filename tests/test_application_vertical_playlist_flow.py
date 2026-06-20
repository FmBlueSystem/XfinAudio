"""Tests for the application-level vertical playlist flow."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import datetime

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


@dataclass(frozen=True)
class FakeRecommendationResult:
    recommendation: PlaylistRecommendation


class FakePlaylistWorkflowService:
    def __init__(self, recommendation: PlaylistRecommendation) -> None:
        self.recommendation = recommendation
        self.calls: list[tuple[list[TrackRecord], str, object | None, float]] = []

    def recommend(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: object | None = None,
        spectral_cohesion: float = 0.0,
    ) -> FakeRecommendationResult:
        self.calls.append((records, strategy_name, controls, spectral_cohesion))
        return FakeRecommendationResult(recommendation=self.recommendation)


class FakeSavedPlaylistService:
    def __init__(self) -> None:
        self.calls: list[tuple[PlaylistRecommendation, str | None]] = []
        self.playlist = Playlist(
            id=42,
            name="First Vertical",
            created_at=datetime(2026, 6, 20),
            updated_at=datetime(2026, 6, 20),
            track_paths=["/music/a.flac", "/music/b.flac"],
        )

    def save_recommendation(
        self,
        recommendation: PlaylistRecommendation,
        *,
        name: str | None = None,
    ) -> Playlist:
        self.calls.append((recommendation, name))
        return self.playlist


def _recommendation() -> PlaylistRecommendation:
    tracks = [
        TrackRecord(path="/music/a.flac", title="A", metadata_status="complete"),
        TrackRecord(path="/music/b.flac", title="B", metadata_status="complete"),
    ]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=default_strategy_registry().get("warmup"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def test_vertical_playlist_flow_recommends_and_saves_without_desktop_imports() -> None:
    import xfinaudio.application.vertical_playlist_flow as vertical_playlist_flow
    from xfinaudio.application import VerticalPlaylistFlow

    source = inspect.getsource(vertical_playlist_flow)
    assert "xfinaudio.desktop" not in source
    assert "PySide6" not in source

    recommendation = _recommendation()
    workflow = FakePlaylistWorkflowService(recommendation)
    saved_playlists = FakeSavedPlaylistService()
    flow = VerticalPlaylistFlow(
        playlist_workflow=workflow,
        saved_playlists=saved_playlists,
    )

    result = flow.recommend_and_save(
        recommendation.ordered_tracks,
        "warmup",
        playlist_name="First Vertical",
    )

    assert workflow.calls == [(recommendation.ordered_tracks, "warmup", None, 0.0)]
    assert saved_playlists.calls == [(recommendation, "First Vertical")]
    assert result.recommendation is recommendation
    assert result.playlist == saved_playlists.playlist
