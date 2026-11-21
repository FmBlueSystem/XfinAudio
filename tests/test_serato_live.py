"""Read-only access to what Serato DJ plays, and its match against the library (S1, S2).

The tests build their own small SQLite file with the two tables S1 names, so nothing
here ever opens the real Serato database. A file that cannot be read must always
answer "not available" with a reason, never raise, and never change a byte.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from xfinaudio.headless.serato_live import (
    MAX_PLAYED_ENTRIES,
    NO_SESSION,
    SERATO_BUSY,
    SERATO_NOT_FOUND,
    SERATO_UNREADABLE,
    SeratoEntry,
    match_library_path,
    read_serato_snapshot,
)

_LOSSLESS = "_Lossless/por_genero/House/Whitney Houston - It's Not Right.flac"


def _build_database(
    path: Path,
    sessions: list[tuple[int, int, int]],
    entries: list[tuple[int, int, int, int, int, int, str, str, float | None, str, str]],
) -> None:
    """Create the two tables S1 names, with only the columns S1 names."""
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE history_session (id INTEGER PRIMARY KEY, start_time INTEGER, end_time INTEGER)"
        )
        connection.execute(
            "CREATE TABLE history_entry ("
            "id INTEGER PRIMARY KEY, session_id INTEGER, deck INTEGER, played INTEGER, "
            "start_time INTEGER, end_time INTEGER, name TEXT, artist TEXT, bpm REAL, key TEXT, portable_id TEXT)"
        )
        connection.executemany("INSERT INTO history_session VALUES (?, ?, ?)", sessions)
        connection.executemany("INSERT INTO history_entry VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", entries)


def _entry(
    entry_id: int,
    *,
    session_id: int = 7,
    deck: int = 1,
    start_time: int = 1_700_000_000,
    end_time: int = -1,
    name: str = "Track",
    artist: str = "Artist",
    bpm: float | None = 128.0,
    key: str = "8A",
    portable_id: str = _LOSSLESS,
) -> tuple[int, int, int, int, int, int, str, str, float | None, str, str]:
    return (entry_id, session_id, deck, 1, start_time, end_time, name, artist, bpm, key, portable_id)


def test_open_entries_are_one_per_deck_newest_start_first(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _build_database(
        database,
        [(7, 1_699_000_000, -1)],
        [
            _entry(1, deck=1, start_time=100, name="Old deck one"),
            _entry(2, deck=1, start_time=300, name="New deck one"),
            _entry(3, deck=2, start_time=200, name="Deck two"),
            _entry(4, deck=1, start_time=400, end_time=500, name="Already played"),
        ],
    )

    snapshot = read_serato_snapshot(database)

    assert snapshot.available is True
    assert snapshot.reason is None
    assert snapshot.session_id == 7
    assert snapshot.session_started_at == 1_699_000_000
    assert [entry.title for entry in snapshot.playing] == ["New deck one", "Deck two"]
    assert [entry.deck for entry in snapshot.playing] == [1, 2]
    assert [entry.start_time for entry in snapshot.playing] == [300, 200]


def test_ended_entries_are_newest_first_and_capped_at_fifty(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    ended = [_entry(index, deck=1, start_time=index, end_time=index + 1, name=f"Played {index}") for index in range(60)]
    _build_database(
        database,
        [(7, 1_699_000_000, -1)],
        [*ended, _entry(100, deck=2, start_time=999, name="Still loaded")],
    )

    snapshot = read_serato_snapshot(database)

    assert len(snapshot.played) == MAX_PLAYED_ENTRIES == 50
    assert [entry.start_time for entry in snapshot.played] == list(range(59, 9, -1))
    assert all(entry.end_time != -1 for entry in snapshot.played)
    assert [entry.title for entry in snapshot.playing] == ["Still loaded"]


def test_only_the_newest_session_is_read(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _build_database(
        database,
        [(3, 1_690_000_000, 1_695_000_000), (9, 1_699_000_000, -1)],
        [
            _entry(1, session_id=3, deck=1, start_time=10, name="Old session playing"),
            _entry(2, session_id=3, deck=1, start_time=20, end_time=30, name="Old session played"),
            _entry(3, session_id=9, deck=2, start_time=40, name="New session playing"),
            _entry(4, session_id=9, deck=2, start_time=50, end_time=60, name="New session played"),
        ],
    )

    snapshot = read_serato_snapshot(database)

    assert snapshot.session_id == 9
    assert snapshot.session_started_at == 1_699_000_000
    assert [entry.title for entry in snapshot.playing] == ["New session playing"]
    assert [entry.title for entry in snapshot.played] == ["New session played"]


def test_a_missing_file_is_not_available(tmp_path: Path) -> None:
    snapshot = read_serato_snapshot(tmp_path / "missing" / "master.sqlite")

    assert snapshot.available is False
    assert snapshot.reason == SERATO_NOT_FOUND
    assert snapshot.session_id is None
    assert snapshot.playing == () and snapshot.played == ()


def test_a_non_sqlite_file_is_not_available(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    database.write_bytes(b"this is not a sqlite database" * 64)

    snapshot = read_serato_snapshot(database)

    assert snapshot.available is False
    assert snapshot.reason == SERATO_UNREADABLE
    assert snapshot.playing == () and snapshot.played == ()


def test_a_file_without_the_history_tables_is_not_available(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE something_else (id INTEGER PRIMARY KEY)")

    snapshot = read_serato_snapshot(database)

    assert snapshot.available is False
    assert snapshot.reason == SERATO_UNREADABLE


def test_a_locked_database_is_not_available(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _build_database(database, [(7, 1_699_000_000, -1)], [_entry(1)])
    locker = sqlite3.connect(database)
    locker.isolation_level = None
    locker.execute("BEGIN EXCLUSIVE")
    try:
        snapshot = read_serato_snapshot(database)
    finally:
        locker.execute("ROLLBACK")
        locker.close()

    assert snapshot.available is False
    assert snapshot.reason == SERATO_BUSY
    assert snapshot.playing == () and snapshot.played == ()


def test_no_session_is_reported_without_raising(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _build_database(database, [], [])

    snapshot = read_serato_snapshot(database)

    assert snapshot.available is False
    assert snapshot.reason == NO_SESSION
    assert snapshot.session_id is None


def test_reading_leaves_the_database_byte_identical(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _build_database(
        database,
        [(7, 1_699_000_000, -1)],
        [_entry(1, deck=1), _entry(2, deck=2, start_time=200), _entry(3, end_time=300, start_time=250)],
    )
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    snapshot = read_serato_snapshot(database)

    assert snapshot.available is True
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["master.sqlite"]


def test_the_public_shape_carries_serato_fields_and_never_a_path(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _build_database(database, [(7, 1_699_000_000, -1)], [_entry(1, deck=2, start_time=250)])

    published = read_serato_snapshot(database).public()

    assert published["available"] is True
    assert published["reason"] is None
    assert published["sessionStartedAt"] == 1_699_000_000
    playing = published["playing"][0]
    assert playing == {
        "deck": 2,
        "startedAt": 250,
        "title": "Track",
        "artist": "Artist",
        "bpm": 128.0,
        "key": "8A",
    }
    assert "portableId" not in playing and "path" not in playing


def _serato_entry(portable_id: str) -> SeratoEntry:
    return SeratoEntry(
        deck=1,
        session_id=7,
        start_time=250,
        end_time=-1,
        title="Track",
        artist="Artist",
        bpm=128.0,
        key="8A",
        portable_id=portable_id,
    )


def test_a_library_path_that_ends_with_the_portable_id_matches() -> None:
    library = ["/Volumes/dd/Other/x.flac", f"/Volumes/dd/{_LOSSLESS}"]

    assert match_library_path(_serato_entry(_LOSSLESS), library) == f"/Volumes/dd/{_LOSSLESS}"


def test_a_path_suffix_match_wins_over_an_earlier_file_name_match() -> None:
    library = ["/Volumes/dd/_Other/Whitney Houston - It's Not Right.flac", f"/Volumes/dd/{_LOSSLESS}"]

    assert match_library_path(_serato_entry(_LOSSLESS), library) == f"/Volumes/dd/{_LOSSLESS}"


def test_a_case_insensitive_suffix_match_wins_over_an_exact_file_name_match() -> None:
    library = [
        "/Volumes/dd/_Other/Whitney Houston - It's Not Right.flac",
        "/Volumes/dd/_lossless/por_genero/house/whitney houston - it's not right.FLAC",
    ]

    assert match_library_path(_serato_entry(_LOSSLESS), library) == library[1]


def test_an_exact_case_match_wins_over_a_case_insensitive_one() -> None:
    library = [
        "/Volumes/dd/_lossless/POR_GENERO/House/whitney houston - it's not right.FLAC",
        f"/Volumes/dd/{_LOSSLESS}",
    ]

    assert match_library_path(_serato_entry(_LOSSLESS), library) == f"/Volumes/dd/{_LOSSLESS}"


def test_the_suffix_matches_case_insensitively_when_no_exact_case_does() -> None:
    library = ["/Volumes/dd/_lossless/por_genero/house/whitney houston - it's not right.FLAC"]

    assert match_library_path(_serato_entry(_LOSSLESS), library) == library[0]


def test_the_same_file_name_matches_when_the_path_does_not() -> None:
    library = ["/Volumes/dd/_Other/Whitney Houston - It's Not Right.flac"]

    assert match_library_path(_serato_entry(_LOSSLESS), library) == library[0]


def test_the_same_file_name_matches_case_insensitively() -> None:
    library = ["/Volumes/dd/_Other/whitney houston - it's not right.FLAC"]

    assert match_library_path(_serato_entry(_LOSSLESS), library) == library[0]


@pytest.mark.parametrize("portable_id", ["", "_Lossless/Missing/Unknown - Track.flac"])
def test_an_unmatched_entry_is_not_in_the_library(portable_id: str) -> None:
    library = ["/Volumes/dd/_Lossless/por_genero/House/Whitney Houston - It's Not Right.flac"]

    assert match_library_path(_serato_entry(portable_id), library) is None
