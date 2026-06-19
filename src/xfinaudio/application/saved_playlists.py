"""Application service for saved-playlist use cases."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist
from xfinaudio.library.ports import PlaylistRepositoryPort
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


@dataclass(frozen=True)
class SavedPlaylistExport:
    """Application result for exporting a saved playlist."""

    playlist: Playlist
    recommendation: PlaylistRecommendation


class SavedPlaylistService:
    """Coordinate saved-playlist use cases without UI dependencies."""

    def __init__(
        self,
        *,
        repository: PlaylistRepositoryPort,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now = now

    def create_empty_playlist(self, name: str) -> Playlist:
        return self._repository.create(name, [])

    def rename_playlist(self, playlist_id: int, name: str) -> None:
        self._repository.update_name(playlist_id, name)

    def duplicate_playlist(self, playlist_id: int) -> Playlist:
        return self._repository.duplicate(playlist_id)

    def delete_playlist(self, playlist_id: int) -> None:
        self._repository.delete(playlist_id)

    def save_track_order(self, playlist_id: int, track_paths: list[str]) -> None:
        self._repository.update_tracks(playlist_id, track_paths)

    def save_recommendation(
        self,
        recommendation: PlaylistRecommendation,
        *,
        name: str | None = None,
    ) -> Playlist:
        playlist_name = name or self.default_recommendation_name(recommendation)
        track_paths = [track.path for track in recommendation.ordered_tracks]
        return self._repository.create(playlist_name, track_paths)

    def build_export_recommendation(
        self,
        playlist_id: int,
        scanned_records: Sequence[TrackRecord],
    ) -> SavedPlaylistExport | None:
        playlist = self._repository.get_by_id(playlist_id)
        if playlist is None:
            return None
        tracks_by_path = {track.path: track for track in scanned_records}
        tracks = [
            tracks_by_path.get(path) or TrackRecord(path=path, title=Path(path).stem, metadata_status="complete")
            for path in playlist.track_paths
        ]
        recommendation = PlaylistRecommendation(
            ordered_tracks=tracks,
            transition_scores=[],
            strategy=default_strategy_registry().get("build"),
            warnings=[],
            applied_controls={},
            optimizer="saved-playlist",
            total_score=0.0,
        )
        return SavedPlaylistExport(playlist=playlist, recommendation=recommendation)

    def default_recommendation_name(self, recommendation: PlaylistRecommendation) -> str:
        now = self._now or datetime.now
        date_text = now().strftime("%Y%m%d-%H%M%S")
        return f"{recommendation.strategy.name} - {date_text}"


__all__ = ["SavedPlaylistExport", "SavedPlaylistService"]
