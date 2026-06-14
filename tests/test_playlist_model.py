"""Tests for Playlist domain models."""

from __future__ import annotations

from datetime import datetime

from xfinaudio.library.playlist_models import Playlist, PlaylistSummary


class TestPlaylist:
    def test_construction(self) -> None:
        p = Playlist(
            id=1,
            name="Friday Set",
            created_at=datetime(2026, 6, 8, 10, 0, 0),
            updated_at=datetime(2026, 6, 8, 10, 0, 0),
            track_paths=["/music/a.flac", "/music/b.flac"],
        )
        assert p.id == 1
        assert p.name == "Friday Set"
        assert len(p.track_paths) == 2

    def test_id_none_when_unpersisted(self) -> None:
        p = Playlist(
            id=None,
            name="Draft",
            created_at=datetime(2026, 6, 8, 10, 0, 0),
            updated_at=datetime(2026, 6, 8, 10, 0, 0),
            track_paths=[],
        )
        assert p.id is None

    def test_empty_track_paths(self) -> None:
        p = Playlist(
            id=1,
            name="Empty",
            created_at=datetime(2026, 6, 8, 10, 0, 0),
            updated_at=datetime(2026, 6, 8, 10, 0, 0),
            track_paths=[],
        )
        assert p.track_paths == []


class TestPlaylistSummary:
    def test_construction(self) -> None:
        s = PlaylistSummary(
            id=1,
            name="Friday Set",
            track_count=12,
            updated_at=datetime(2026, 6, 8, 10, 0, 0),
        )
        assert s.id == 1
        assert s.name == "Friday Set"
        assert s.track_count == 12
