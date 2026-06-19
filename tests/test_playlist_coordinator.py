"""Tests for PlaylistCoordinator orchestration."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from xfinaudio.desktop.playlist_coordinator import PlaylistCoordinator
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist, PlaylistSummary
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


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


def _host(recommendation: PlaylistRecommendation | None = None):
    playlist = Playlist(
        id=12,
        name="Saved Set",
        created_at=datetime(2026, 6, 8),
        updated_at=datetime(2026, 6, 8),
        track_paths=["/music/a.flac", "/music/b.flac"],
    )
    repository = MagicMock()
    repository.create.return_value = playlist
    repository.get_by_id.return_value = playlist
    repository.list_summaries.return_value = [
        PlaylistSummary(id=1, name="Saved", track_count=2, updated_at=datetime(2026, 6, 8))
    ]
    return SimpleNamespace(
        _playlist_repository=repository,
        _playlists_screen=MagicMock(),
        _playlist_editor=MagicMock(),
        _export_coordinator=MagicMock(),
        workflow_tabs=MagicMock(),
        last_recommendation=recommendation,
        scanned_records=[] if recommendation is None else recommendation.ordered_tracks,
        tr=lambda text: text,
        _sync_state=MagicMock(),
    )


def test_save_recommendation_persists_tracks_with_default_strategy_date_name() -> None:
    host = _host(_recommendation())

    with patch("xfinaudio.application.saved_playlists.datetime") as datetime_mock:
        datetime_mock.now.return_value = datetime(2026, 6, 15, 9, 8, 7)
        PlaylistCoordinator(host).save_recommendation()  # type: ignore[arg-type]

    name, paths = host._playlist_repository.create.call_args.args
    assert name == "warmup - 20260615-090807"
    assert paths == ["/music/a.flac", "/music/b.flac"]
    host._playlists_screen.populate_list.assert_called_once()
    host.workflow_tabs.setCurrentIndex.assert_called_once_with(4)
    host._sync_state.assert_called_once()


def test_save_recommendation_uses_explicit_name() -> None:
    host = _host(_recommendation())

    PlaylistCoordinator(host).save_recommendation("Custom Set")  # type: ignore[arg-type]

    assert host._playlist_repository.create.call_args.args == ("Custom Set", ["/music/a.flac", "/music/b.flac"])


def test_export_playlist_delegates_saved_tracks_to_serato_export_flow() -> None:
    host = _host(_recommendation())

    PlaylistCoordinator(host).export_playlist(12)  # type: ignore[arg-type]

    host._playlist_editor.set_playlist.assert_called_once_with(host._playlist_repository.get_by_id.return_value)
    host._export_coordinator.export_recommendation_to_serato.assert_called_once_with(crate_name="Saved Set")
    assert [track.path for track in host.last_recommendation.ordered_tracks] == ["/music/a.flac", "/music/b.flac"]


def test_export_playlist_replaces_app_state_when_host_supports_state_transition() -> None:
    host = _host(_recommendation())
    host._state = object()
    host._replace_app_state = MagicMock()
    next_state = object()

    with patch("xfinaudio.desktop.playlist_coordinator.apply_saved_playlist_export_recommendation") as transition:
        transition.return_value = next_state
        PlaylistCoordinator(host).export_playlist(12)  # type: ignore[arg-type]

    transition.assert_called_once()
    assert transition.call_args.args[0] is host._state
    assert [track.path for track in transition.call_args.args[1].ordered_tracks] == ["/music/a.flac", "/music/b.flac"]
    host._replace_app_state.assert_called_once_with(next_state)
    host._export_coordinator.export_recommendation_to_serato.assert_called_once_with(crate_name="Saved Set")
