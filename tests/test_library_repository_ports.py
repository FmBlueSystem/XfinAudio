"""Architecture tests for library repository ports."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.ports import PlaylistRepositoryPort, TrackDisplayRepositoryPort, TrackRepositoryPort
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
