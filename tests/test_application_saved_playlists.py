"""Tests for saved-playlist application use cases."""

from __future__ import annotations

from datetime import datetime

from xfinaudio.application.saved_playlists import SavedPlaylistService
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist, PlaylistSummary
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


class FakePlaylistRepository:
    def __init__(self) -> None:
        self.created: list[tuple[str, list[str]]] = []
        self.updated_names: list[tuple[int, str]] = []
        self.updated_tracks: list[tuple[int, list[str]]] = []
        self.duplicated: list[int] = []
        self.deleted: list[int] = []
        self.playlists: dict[int, Playlist] = {
            7: Playlist(
                id=7,
                name="Saved Set",
                created_at=datetime(2026, 6, 19),
                updated_at=datetime(2026, 6, 19),
                track_paths=["/music/a.flac", "/missing/c.flac"],
            )
        }

    def create(self, name: str, track_paths: list[str]) -> Playlist:
        self.created.append((name, list(track_paths)))
        playlist_id = len(self.created)
        playlist = Playlist(
            id=playlist_id,
            name=name,
            created_at=datetime(2026, 6, 19),
            updated_at=datetime(2026, 6, 19),
            track_paths=list(track_paths),
        )
        self.playlists[playlist_id] = playlist
        return playlist

    def list_summaries(self) -> list[PlaylistSummary]:
        return []

    def get_by_id(self, playlist_id: int) -> Playlist | None:
        return self.playlists.get(playlist_id)

    def update_name(self, playlist_id: int, name: str) -> None:
        self.updated_names.append((playlist_id, name))

    def update_tracks(self, playlist_id: int, track_paths: list[str]) -> None:
        self.updated_tracks.append((playlist_id, list(track_paths)))

    def duplicate(self, playlist_id: int) -> Playlist:
        self.duplicated.append(playlist_id)
        return self.playlists[playlist_id]

    def delete(self, playlist_id: int) -> None:
        self.deleted.append(playlist_id)


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


def test_save_recommendation_uses_default_strategy_date_name() -> None:
    repository = FakePlaylistRepository()
    service = SavedPlaylistService(repository=repository, now=lambda: datetime(2026, 6, 15, 9, 8, 7))

    playlist = service.save_recommendation(_recommendation())

    assert playlist.name == "warmup - 20260615-090807"
    assert repository.created == [("warmup - 20260615-090807", ["/music/a.flac", "/music/b.flac"])]


def test_save_recommendation_uses_explicit_name() -> None:
    repository = FakePlaylistRepository()
    service = SavedPlaylistService(repository=repository)

    service.save_recommendation(_recommendation(), name="Custom Set")

    assert repository.created[-1] == ("Custom Set", ["/music/a.flac", "/music/b.flac"])


def test_playlist_commands_delegate_to_repository_port() -> None:
    repository = FakePlaylistRepository()
    service = SavedPlaylistService(repository=repository)

    service.create_empty_playlist("New Playlist")
    service.rename_playlist(7, "Renamed")
    service.duplicate_playlist(7)
    service.delete_playlist(7)
    service.save_track_order(7, ["/music/z.flac"])

    assert repository.created[-1] == ("New Playlist", [])
    assert repository.updated_names == [(7, "Renamed")]
    assert repository.duplicated == [7]
    assert repository.deleted == [7]
    assert repository.updated_tracks == [(7, ["/music/z.flac"])]


def test_build_export_recommendation_uses_scanned_records_and_missing_fallbacks() -> None:
    repository = FakePlaylistRepository()
    service = SavedPlaylistService(repository=repository)
    scanned = [TrackRecord(path="/music/a.flac", title="A scanned", metadata_status="complete")]

    result = service.build_export_recommendation(7, scanned)

    assert result is not None
    assert result.playlist.name == "Saved Set"
    recommendation = result.recommendation
    assert [track.title for track in recommendation.ordered_tracks] == ["A scanned", "c"]
    assert [track.path for track in recommendation.ordered_tracks] == ["/music/a.flac", "/missing/c.flac"]
    assert recommendation.optimizer == "saved-playlist"
    assert recommendation.strategy.name == "build"


def test_build_export_recommendation_returns_none_for_missing_playlist() -> None:
    service = SavedPlaylistService(repository=FakePlaylistRepository())

    assert service.build_export_recommendation(999, []) is None
