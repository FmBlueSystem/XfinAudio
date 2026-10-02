"""Atomic optimistic updates preserve both names and track order on conflicts/failure."""

import sqlite3
from pathlib import Path

import pytest

from xfinaudio.library.playlist_repository import PlaylistRepository


def test_atomic_name_and_order_update_rejects_concurrent_revision(tmp_path: Path) -> None:
    repository = PlaylistRepository(tmp_path / "playlists.db")
    original = repository.create("Original", ["a", "b", "a"])
    assert original.id is not None
    saved = repository.compare_and_update(original, name="Edited", track_paths=["b", "a"])
    assert saved is not None and saved.name == "Edited" and saved.track_paths == ["b", "a"]
    assert repository.compare_and_update(original, name="Stale", track_paths=[]) is None
    assert repository.get_by_id(original.id) == saved
    repository.update_tracks(original.id, ["a"])
    assert repository.compare_and_update(saved, name="Also stale", track_paths=["b"]) is None
    assert repository.get_by_id(original.id).name == "Edited"
    assert repository.get_by_id(original.id).track_paths == ["a"]


def test_atomic_edit_rolls_back_name_and_tracks_on_insert_failure(tmp_path: Path, monkeypatch) -> None:
    repository = PlaylistRepository(tmp_path / "playlists.db")
    original = repository.create("Original", ["a", "b"])
    assert original.id is not None

    def fail_after_partial_insert(connection, playlist_id, paths):
        connection.execute("INSERT INTO playlist_tracks VALUES (?, ?, ?)", (playlist_id, paths[0], 0))
        raise sqlite3.IntegrityError("synthetic write failure")

    monkeypatch.setattr(repository, "_insert_tracks", fail_after_partial_insert)
    with pytest.raises(sqlite3.IntegrityError):
        repository.compare_and_update(original, name="Must rollback", track_paths=["b", "a"])
    assert repository.get_by_id(original.id) == original


def test_atomic_edit_rejects_deleted_playlist(tmp_path: Path) -> None:
    repository = PlaylistRepository(tmp_path / "playlists.db")
    original = repository.create("Original", ["a"])
    assert original.id is not None
    repository.delete(original.id)
    assert repository.compare_and_update(original, name="Deleted", track_paths=[]) is None


def test_atomic_edit_accepts_legacy_sqlite_timestamp_spelling(tmp_path: Path) -> None:
    repository = PlaylistRepository(tmp_path / "playlists.db")
    original = repository.create("Legacy", ["a", "b"])
    assert original.id is not None
    with repository._connect() as connection:
        connection.execute(
            "UPDATE playlists SET created_at = ?, updated_at = ? WHERE id = ?",
            ("2020-01-01 12:00:00", "2020-01-01 12:00:00", original.id),
        )
    original = repository.get_by_id(original.id)
    assert original is not None
    saved = repository.compare_and_update(original, name="Edited legacy", track_paths=["b", "a"])
    assert saved is not None
    assert saved.name == "Edited legacy"


def test_concurrent_writers_cannot_both_commit_one_revision(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    repository = PlaylistRepository(tmp_path / "playlists.db")
    original = repository.create("Original", ["a", "b"])
    assert original.id is not None
    barrier = Barrier(2)

    def update(name):
        barrier.wait()
        return repository.compare_and_update(original, name=name, track_paths=[name])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, ["first", "second"]))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert repository.get_by_id(original.id) == winners[0]
