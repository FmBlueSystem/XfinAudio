"""Architecture tests for library repository ports."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.ports import (
    PlaylistRepositoryPort,
    TrackDanceabilityProfileCachePort,
    TrackDanceabilityProfileCacheReaderPort,
    TrackDisplayRepositoryPort,
    TrackRepositoryPort,
)
from xfinaudio.library.track_repository import TrackRepository


class FakeScanService:
    def scan(self, *args: object, **kwargs: object) -> list[TrackRecord]:
        return []


def test_playlist_coordinator_depends_on_playlist_repository_port() -> None:
    source = Path("src/xfinaudio/desktop/playlist_coordinator.py").read_text()

    assert "xfinaudio.library.ports import PlaylistRepositoryPort" in source
    assert "xfinaudio.library.playlist_repository" not in source


def test_playlist_workflow_uses_shared_track_repository_port() -> None:
    source = Path("src/xfinaudio/application/playlist_workflow.py").read_text()

    assert "xfinaudio.library.ports import TrackRepositoryPort" in source
    assert "class TrackPersistence" not in source
    assert "repository: TrackRepositoryPort" in source


def test_concrete_repositories_satisfy_repository_ports(tmp_path: Path) -> None:
    track_port: TrackRepositoryPort = TrackRepository(tmp_path / "tracks.db")
    display_port: TrackDisplayRepositoryPort = TrackRepository(tmp_path / "tracks.db")
    playlist_port: PlaylistRepositoryPort = PlaylistRepository(tmp_path / "playlists.db")

    track_port.save_scan_results([])
    assert display_port.list_display_tracks() == []
    created = playlist_port.create("Warmup", [])
    assert created.id is not None
    assert playlist_port.get_by_id(created.id) == created


def test_playlist_workflow_accepts_track_repository_port(tmp_path: Path) -> None:
    repository: TrackRepositoryPort = TrackRepository(tmp_path / "tracks.db")
    workflow = PlaylistWorkflowService(scan_service=FakeScanService(), repository=repository)

    assert workflow.repository is repository


def test_concrete_repository_satisfies_danceability_profile_ports(tmp_path: Path) -> None:
    repository = TrackRepository(tmp_path / "tracks.db")
    reader: TrackDanceabilityProfileCacheReaderPort = repository
    writer: TrackDanceabilityProfileCachePort = repository
    profile = DanceabilityProfile(
        score=0.72,
        pulse_clarity=0.8,
        tempo_confidence=0.9,
        percussive_ratio=0.6,
    )

    repository.save_scan_results([TrackRecord(path="/music/track.flac")])

    assert writer.update_danceability_profile("/music/track.flac", profile) is True
    assert reader.load_danceability_profile_cache(["/music/track.flac"]) == {}
