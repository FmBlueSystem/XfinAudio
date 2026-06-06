import sqlite3

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import (
    SCHEMA_VERSION,
    DatabaseSchemaError,
    TrackRepository,
    UnsupportedDatabaseVersionError,
)


def test_track_repository_persists_and_round_trips_scan_records(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        artist="Artist One",
        bpm=116.0,
        camelot_key="11B",
        energy_level=7,
        genre="Disco",
        tags=["Disco", "Classic"],
        metadata_status="complete",
        missing_required_fields=[],
        source_fields={"bpm": "bpm", "camelot_key": "key", "energy_level": "energy"},
        raw_metadata={"title": ["Track One"], "bpm": ["116.0"]},
    )

    repository.save_scan_results([original])

    assert repository.list_tracks() == [original]


def test_track_repository_replaces_existing_record_for_same_path(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    first = TrackRecord(path="/music/track.flac", title="Old", metadata_status="incomplete")
    second = TrackRecord(path="/music/track.flac", title="New", metadata_status="complete", bpm=120.0)

    repository.save_scan_results([first])
    repository.save_scan_results([second])

    assert repository.list_tracks() == [second]


def test_track_repository_initializes_schema_user_version(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"

    TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_track_repository_rejects_future_schema_without_resetting_version(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    future_version = SCHEMA_VERSION + 1
    with sqlite3.connect(db_path) as connection:
        connection.execute(f"PRAGMA user_version = {future_version}")

    with pytest.raises(UnsupportedDatabaseVersionError, match="Unsupported database schema version"):
        TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == future_version


def test_track_repository_accepts_current_schema_version(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    TrackRepository(db_path)

    repository = TrackRepository(db_path)

    assert repository.list_tracks() == []


def test_track_repository_rejects_unversioned_partial_tracks_table_without_marking_v1(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE tracks (path TEXT PRIMARY KEY, title TEXT)")
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0

    with pytest.raises(DatabaseSchemaError, match="Unversioned database contains an existing tracks table"):
        TrackRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0


def test_track_repository_list_display_tracks_omits_large_raw_metadata_for_ui(tmp_path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    repository = TrackRepository(db_path)
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        artist="Artist One",
        bpm=116.0,
        camelot_key="11B",
        energy_level=7,
        genre="Disco",
        tags=["Disco", "Classic"],
        metadata_status="complete",
        missing_required_fields=[],
        source_fields={"bpm": "bpm"},
        raw_metadata={"huge": ["payload"]},
    )

    repository.save_scan_results([original])

    display_records = repository.list_display_tracks()

    assert display_records == [
        TrackRecord(
            path="/music/track.flac",
            title="Track One",
            artist="Artist One",
            bpm=116.0,
            camelot_key="11B",
            energy_level=7,
            genre="Disco",
            tags=["Disco", "Classic"],
            metadata_status="complete",
            missing_required_fields=[],
        )
    ]
