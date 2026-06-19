"""Repository contracts for library persistence boundaries."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist, PlaylistSummary


class TrackRepositoryPort(Protocol):
    """Contract for scan-result persistence used by application workflows."""

    def save_scan_results(self, records: list[TrackRecord]) -> None:
        """Persist scanned track records."""
        ...


class TrackDisplayRepositoryPort(Protocol):
    """Contract for display-ready track listing."""

    def list_display_tracks(self) -> list[TrackRecord]:
        """Return tracks suitable for display without large raw metadata blobs."""
        ...


class TrackSpectralProfileCacheReaderPort(Protocol):
    """Contract for reading cached spectral profiles."""

    def load_spectral_profile_cache(
        self,
        paths: Iterable[str],
    ) -> dict[str, tuple[int, int, SpectralProfile]]:
        """Return cached spectral profiles keyed by track path."""
        ...


class TrackSpectralProfileCachePort(TrackSpectralProfileCacheReaderPort, Protocol):
    """Contract for cached spectral profile persistence."""

    def update_spectral_profile(self, path: str, profile: SpectralProfile) -> bool:
        """Persist a spectral profile for a single track."""
        ...


class PlaylistRepositoryPort(Protocol):
    """Contract for saved-playlist persistence."""

    def create(self, name: str, track_paths: list[str]) -> Playlist:
        """Create a saved playlist."""
        ...

    def list_summaries(self) -> list[PlaylistSummary]:
        """Return lightweight saved-playlist summaries."""
        ...

    def get_by_id(self, playlist_id: int) -> Playlist | None:
        """Fetch a saved playlist by id."""
        ...

    def update_name(self, playlist_id: int, name: str) -> None:
        """Rename a saved playlist."""
        ...

    def update_tracks(self, playlist_id: int, track_paths: list[str]) -> None:
        """Replace tracks in a saved playlist."""
        ...

    def duplicate(self, playlist_id: int) -> Playlist:
        """Duplicate a saved playlist."""
        ...

    def delete(self, playlist_id: int) -> None:
        """Delete a saved playlist."""
        ...


__all__ = [
    "PlaylistRepositoryPort",
    "TrackDisplayRepositoryPort",
    "TrackRepositoryPort",
    "TrackSpectralProfileCachePort",
    "TrackSpectralProfileCacheReaderPort",
]
