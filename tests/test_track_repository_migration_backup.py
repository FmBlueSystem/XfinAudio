"""Copy the library database before migrating it and restore it on failure (S10).

A DJ's ``tracks.db`` holds a full library scan. The migration runs its DDL inside
``BEGIN IMMEDIATE``, but the free-page reclaim (VACUUM) runs in a second
connection outside that transaction, so a failure there -- or a crash right after
the commit -- could leave a half-upgraded file with no way back. These tests pin
the pre-migration copy, the restore and the cases that must not copy at all.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from xfinaudio.library import track_repository
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import (
    SCHEMA_VERSION,
    DatabaseBackupError,
    DatabaseSchemaError,
    TrackRepository,
    UnsupportedDatabaseVersionError,
)

# Schema v4 introduced the raw-metadata allowlist, so a v3 database still holds
# untrimmed blobs and the upgrade both trims them and reclaims the free pages.
LEGACY_VERSION = 3
LEGACY_PATH = "/music/legacy.flac"
UNPARSEABLE_RAW = {"title": ["Legacy"], "bpm": ["120.0"], "beatgrid": "A" * 5000, "serato_overview": "B" * 5000}
TRIMMED_RAW = {"title": ["Legacy"], "bpm": ["120.0"]}


def legacy_database(parent: Path) -> Path:
    """A database written before the raw-metadata allowlist, holding one track."""
    db_path = parent / "tracks.db"
    repository = TrackRepository(db_path)
    repository.save_scan_results(
        [TrackRecord(path=LEGACY_PATH, title="Legacy", metadata_status="complete", raw_metadata=dict(UNPARSEABLE_RAW))]
    )
    with sqlite3.connect(db_path) as connection:
        connection.execute(f"PRAGMA user_version = {LEGACY_VERSION}")
    return db_path


def user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return connection.execute("PRAGMA user_version").fetchone()[0]


def stored_raw_metadata(path: Path) -> dict[str, object]:
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT raw_metadata_json FROM tracks WHERE path = ?", (LEGACY_PATH,)).fetchone()
    assert row is not None
    return json.loads(row[0])


def assert_openable_with_one_legacy_track(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT path FROM tracks").fetchall() == [(LEGACY_PATH,)]


def test_failed_trim_step_restores_the_previous_database(tmp_path, monkeypatch) -> None:
    db_path = legacy_database(tmp_path)

    def explode(connection: sqlite3.Connection) -> None:
        raise RuntimeError("simulated trim failure")

    monkeypatch.setattr(TrackRepository, "_trim_legacy_raw_metadata", staticmethod(explode))

    with pytest.raises(RuntimeError, match="simulated trim failure"):
        TrackRepository(db_path)

    assert user_version(db_path) == LEGACY_VERSION
    assert stored_raw_metadata(db_path) == UNPARSEABLE_RAW
    assert_openable_with_one_legacy_track(db_path)


def test_failed_reclaim_after_commit_restores_the_previous_database(tmp_path, monkeypatch) -> None:
    db_path = legacy_database(tmp_path)

    def explode(self: TrackRepository) -> None:
        raise RuntimeError("simulated vacuum failure")

    monkeypatch.setattr(TrackRepository, "_reclaim_free_pages", explode)

    with pytest.raises(RuntimeError, match="simulated vacuum failure"):
        TrackRepository(db_path)

    # The DDL and trim had already committed before the reclaim ran, so only the
    # restore can bring the old schema version and the untrimmed rows back.
    assert user_version(db_path) == LEGACY_VERSION
    assert stored_raw_metadata(db_path) == UNPARSEABLE_RAW
    assert_openable_with_one_legacy_track(db_path)
    assert (tmp_path / "tracks.db.schema-v3.bak").exists()


def test_successful_migration_keeps_rows_and_retains_the_previous_version(tmp_path) -> None:
    db_path = legacy_database(tmp_path)

    repository = TrackRepository(db_path)

    assert [record.title for record in repository.list_tracks()] == ["Legacy"]
    assert user_version(db_path) == SCHEMA_VERSION
    assert stored_raw_metadata(db_path) == TRIMMED_RAW

    backup_path = tmp_path / "tracks.db.schema-v3.bak"
    assert backup_path.exists()
    assert user_version(backup_path) == LEGACY_VERSION
    assert stored_raw_metadata(backup_path) == UNPARSEABLE_RAW
    assert_openable_with_one_legacy_track(backup_path)


def test_failed_backup_refuses_to_migrate_and_leaves_the_database_untouched(tmp_path, monkeypatch) -> None:
    db_path = legacy_database(tmp_path)

    def explode(source: Path, target: Path) -> None:
        raise OSError("simulated disk full")

    monkeypatch.setattr(track_repository, "_copy_database", explode)

    with pytest.raises(DatabaseBackupError, match="Could not copy"):
        TrackRepository(db_path)

    assert user_version(db_path) == LEGACY_VERSION
    assert stored_raw_metadata(db_path) == UNPARSEABLE_RAW
    assert_openable_with_one_legacy_track(db_path)
    # Neither a half-written backup nor a scratch file survives the refusal.
    assert sorted(path.name for path in tmp_path.iterdir()) == ["tracks.db"]


def test_database_at_the_current_version_is_not_copied(tmp_path) -> None:
    db_path = tmp_path / "tracks.db"
    TrackRepository(db_path)

    reopened = TrackRepository(db_path)

    assert reopened.list_tracks() == []
    assert user_version(db_path) == SCHEMA_VERSION
    assert sorted(path.name for path in tmp_path.iterdir()) == ["tracks.db"]


def test_new_and_empty_databases_are_not_copied(tmp_path) -> None:
    fresh = tmp_path / "fresh" / "tracks.db"
    TrackRepository(fresh)
    assert user_version(fresh) == SCHEMA_VERSION
    assert list(fresh.parent.glob("tracks.db.schema-v*.bak")) == []

    empty_parent = tmp_path / "empty"
    empty_parent.mkdir()
    empty = empty_parent / "tracks.db"
    empty.touch()

    repository = TrackRepository(empty)

    assert repository.list_tracks() == []
    assert user_version(empty) == SCHEMA_VERSION
    assert list(empty_parent.iterdir()) == [empty]


def test_refused_databases_keep_their_errors_and_get_no_backup(tmp_path) -> None:
    future = tmp_path / "future.db"
    future_version = SCHEMA_VERSION + 1
    with sqlite3.connect(future) as connection:
        connection.execute(f"PRAGMA user_version = {future_version}")

    with pytest.raises(UnsupportedDatabaseVersionError, match="Unsupported database schema version"):
        TrackRepository(future)

    unversioned = tmp_path / "unversioned.db"
    with sqlite3.connect(unversioned) as connection:
        connection.execute("CREATE TABLE tracks (path TEXT PRIMARY KEY, title TEXT)")

    with pytest.raises(DatabaseSchemaError, match="Unversioned database contains an existing tracks table"):
        TrackRepository(unversioned)

    assert user_version(future) == future_version
    assert user_version(unversioned) == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == ["future.db", "unversioned.db"]


def test_backup_retention_is_bounded_and_keeps_the_new_backup(tmp_path) -> None:
    db_path = legacy_database(tmp_path)
    for version in (1, 2):
        stale = tmp_path / f"tracks.db.schema-v{version}.bak"
        stale.write_bytes(b"stale")
        os.utime(stale, (0, 0))

    TrackRepository(db_path)

    backups = sorted(path.name for path in tmp_path.glob("tracks.db.schema-v*.bak"))
    assert len(backups) == 2
    assert "tracks.db.schema-v3.bak" in backups
