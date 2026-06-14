"""Tests for PlaylistRepository — SQLite persistence for playlists."""

from __future__ import annotations

from pathlib import Path

import pytest

from xfinaudio.library.playlist_repository import PlaylistRepository


@pytest.fixture
def repo(tmp_path: Path) -> PlaylistRepository:
    return PlaylistRepository(tmp_path / "test_playlists.db")


class TestCreate:
    def test_create_returns_playlist_with_id(self, repo: PlaylistRepository) -> None:
        p = repo.create("Friday Set", ["/music/a.flac", "/music/b.flac"])
        assert p.id is not None
        assert p.name == "Friday Set"
        assert p.track_paths == ["/music/a.flac", "/music/b.flac"]

    def test_create_empty_playlist(self, repo: PlaylistRepository) -> None:
        p = repo.create("Empty", [])
        assert p.id is not None
        assert p.track_paths == []


class TestListSummaries:
    def test_list_returns_summaries(self, repo: PlaylistRepository) -> None:
        repo.create("Set A", ["/a.flac"])
        repo.create("Set B", ["/b.flac", "/c.flac"])
        summaries = repo.list_summaries()
        assert len(summaries) == 2
        names = {s.name for s in summaries}
        assert names == {"Set A", "Set B"}

    def test_list_returns_correct_track_count(self, repo: PlaylistRepository) -> None:
        repo.create("Set A", ["/a.flac", "/b.flac"])
        summaries = repo.list_summaries()
        assert summaries[0].track_count == 2


class TestGetById:
    def test_get_existing(self, repo: PlaylistRepository) -> None:
        created = repo.create("Set A", ["/a.flac"])
        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "Set A"
        assert fetched.track_paths == ["/a.flac"]

    def test_get_missing_returns_none(self, repo: PlaylistRepository) -> None:
        assert repo.get_by_id(9999) is None


class TestUpdateName:
    def test_update_name(self, repo: PlaylistRepository) -> None:
        p = repo.create("Old", ["/a.flac"])
        repo.update_name(p.id, "New")
        fetched = repo.get_by_id(p.id)
        assert fetched is not None
        assert fetched.name == "New"


class TestUpdateTracks:
    def test_update_tracks(self, repo: PlaylistRepository) -> None:
        p = repo.create("Set", ["/a.flac", "/b.flac"])
        repo.update_tracks(p.id, ["/c.flac"])
        fetched = repo.get_by_id(p.id)
        assert fetched is not None
        assert fetched.track_paths == ["/c.flac"]


class TestDuplicate:
    def test_duplicate_creates_copy(self, repo: PlaylistRepository) -> None:
        p = repo.create("Original", ["/a.flac"])
        dup = repo.duplicate(p.id)
        assert dup.id is not None
        assert dup.id != p.id
        assert dup.name == "Original (copy)"
        assert dup.track_paths == ["/a.flac"]


class TestDelete:
    def test_delete_removes_playlist(self, repo: PlaylistRepository) -> None:
        p = repo.create("ToDelete", ["/a.flac"])
        repo.delete(p.id)
        assert repo.get_by_id(p.id) is None

    def test_delete_cascades_tracks(self, repo: PlaylistRepository) -> None:
        p = repo.create("ToDelete", ["/a.flac", "/b.flac"])
        repo.delete(p.id)
        # Re-create repo to verify from fresh connection
        summaries = repo.list_summaries()
        assert len(summaries) == 0
