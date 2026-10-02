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
        assert created.id is not None
        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "Set A"
        assert fetched.track_paths == ["/a.flac"]

    def test_get_missing_returns_none(self, repo: PlaylistRepository) -> None:
        assert repo.get_by_id(9999) is None


class TestUpdateName:
    def test_update_name(self, repo: PlaylistRepository) -> None:
        p = repo.create("Old", ["/a.flac"])
        assert p.id is not None
        repo.update_name(p.id, "New")
        fetched = repo.get_by_id(p.id)
        assert fetched is not None
        assert fetched.name == "New"


class TestUpdateTracks:
    def test_update_tracks(self, repo: PlaylistRepository) -> None:
        p = repo.create("Set", ["/a.flac", "/b.flac"])
        assert p.id is not None
        repo.update_tracks(p.id, ["/c.flac"])
        fetched = repo.get_by_id(p.id)
        assert fetched is not None
        assert fetched.track_paths == ["/c.flac"]


class TestDuplicate:
    def test_duplicate_creates_copy(self, repo: PlaylistRepository) -> None:
        p = repo.create("Original", ["/a.flac"])
        assert p.id is not None
        dup = repo.duplicate(p.id)
        assert dup.id is not None
        assert dup.id != p.id
        assert dup.name == "Original (copy)"
        assert dup.track_paths == ["/a.flac"]


class TestDelete:
    def test_delete_removes_playlist(self, repo: PlaylistRepository) -> None:
        p = repo.create("ToDelete", ["/a.flac"])
        assert p.id is not None
        repo.delete(p.id)
        assert repo.get_by_id(p.id) is None

    def test_delete_cascades_tracks(self, repo: PlaylistRepository) -> None:
        p = repo.create("ToDelete", ["/a.flac", "/b.flac"])
        assert p.id is not None
        repo.delete(p.id)
        # Re-create repo to verify from fresh connection
        summaries = repo.list_summaries()
        assert len(summaries) == 0


def test_delete_removes_child_rows_and_enforces_parent_integrity(repo: PlaylistRepository) -> None:
    import sqlite3

    playlist = repo.create("Synthetic", ["/a", "/b"])
    assert playlist.id is not None
    repo.delete(playlist.id)
    with sqlite3.connect(repo.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM playlist_tracks").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    with pytest.raises(sqlite3.IntegrityError):
        repo.update_tracks(99999, ["/orphan"])


def test_existing_orphans_are_migrated_without_changing_valid_tracks(repo: PlaylistRepository) -> None:
    import sqlite3

    playlist = repo.create("Keep", ["/second", "/first"])
    assert playlist.id is not None
    with sqlite3.connect(repo.db_path) as connection:
        connection.execute("INSERT INTO playlist_tracks VALUES (99999, '/orphan', 0)")
    reopened = PlaylistRepository(repo.db_path)
    kept = reopened.get_by_id(playlist.id)
    assert kept is not None
    assert kept.track_paths == ["/second", "/first"]
    with sqlite3.connect(repo.db_path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    PlaylistRepository(repo.db_path)
