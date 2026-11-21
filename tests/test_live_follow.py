"""Suggest the next track from the whole library, following Serato (S3).

The library is a scanned fixture of metadata-only FLAC files and Serato's side is a
small SQLite file the test builds itself, so nothing here ever opens the real Serato
database. Every answer is asked through ``HeadlessBackend.execute("live.follow", {})``,
the public interface the transport uses.
"""

from __future__ import annotations

import io
import json
import sqlite3
import threading
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from tests.test_headless_backend import tagged_flac as _base_flac
from tests.test_headless_protocol import messages, request
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.serato_live import (
    NO_SESSION,
    SERATO_BUSY,
    SERATO_NOT_FOUND,
    SERATO_UNREADABLE,
)
from xfinaudio.headless.server import INLINE_METHODS, JsonlServer

_CURRENT = "House/Whitney Houston - It's Not Right but It's Okay.flac"
_PLAYED = "House/Enrique Iglesias - I Like It.flac"
_VERSION = "House/Whitney Houston - It's Not Right but It's Okay (Club 69 Radio Mix).flac"


def tagged_flac(
    path: Path,
    *,
    title: str,
    artist: str = "Test Artist",
    bpm: float | None = 128.0,
    key: str | None = "8A",
    energy: int | None = 5,
) -> None:
    """A metadata-only FLAC fixture, never used as a playback fixture."""
    _base_flac(path, 0)
    tags = FLAC(path)
    tags["title"] = title
    tags["artist"] = artist
    for name, value in (("bpm", bpm), ("initialkey", key), ("energylevel", energy)):
        if value is None:
            del tags[name]
        else:
            tags[name] = str(value)
    tags.save()


def _database(
    path: Path,
    sessions: list[tuple[int, int, int]],
    entries: list[tuple[int, int, int, int, int, int, str, str, float | None, str, str]],
) -> None:
    """The two tables S1 names, with only the columns S1 names."""
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


def _row(
    entry_id: int,
    *,
    deck: int = 1,
    start_time: int = 1_700_000_100,
    end_time: int = -1,
    name: str = "Track",
    artist: str = "Artist",
    bpm: float | None = 128.0,
    key: str = "8A",
    portable_id: str = _CURRENT,
    session_id: int = 7,
) -> tuple[int, int, int, int, int, int, str, str, float | None, str, str]:
    return (entry_id, session_id, deck, 1, start_time, end_time, name, artist, bpm, key, portable_id)


def _backend(tmp_path: Path) -> HeadlessBackend:
    """A scanned fixture library whose Serato database is a test-owned attribute."""
    return HeadlessBackend(tmp_path / "data")


def _scan(backend: HeadlessBackend, root: Path) -> dict[str, str]:
    return {track["title"]: track["id"] for track in backend.execute("library.scan", {"root": str(root)})["tracks"]}


def _follow(backend: HeadlessBackend) -> dict:
    return backend.execute("live.follow", {})


def test_an_absent_database_answers_serato_not_found(tmp_path: Path) -> None:
    backend = _backend(tmp_path)
    backend.serato_database_path = tmp_path / "master.sqlite"

    answer = _follow(backend)

    assert answer == {
        "available": False,
        "reason": SERATO_NOT_FOUND,
        "sessionStartedAt": None,
        "playing": [],
        "current": None,
        "suggestions": [],
        "playedCount": 0,
    }


def test_a_database_with_an_unknown_schema_answers_serato_unreadable(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE something_else (id INTEGER PRIMARY KEY)")
    backend = _backend(tmp_path)
    backend.serato_database_path = database

    assert _follow(backend)["reason"] == SERATO_UNREADABLE


def test_a_locked_database_answers_serato_busy(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _database(database, [(7, 1_699_000_000, -1)], [_row(1)])
    backend = _backend(tmp_path)
    backend.serato_database_path = database
    locker = sqlite3.connect(database)
    locker.isolation_level = None
    locker.execute("BEGIN EXCLUSIVE")
    try:
        answer = _follow(backend)
    finally:
        locker.execute("ROLLBACK")
        locker.close()

    assert answer["available"] is False
    assert answer["reason"] == SERATO_BUSY
    assert answer["playing"] == []


def test_an_empty_history_answers_no_session(tmp_path: Path) -> None:
    database = tmp_path / "master.sqlite"
    _database(database, [], [])
    backend = _backend(tmp_path)
    backend.serato_database_path = database

    assert _follow(backend)["reason"] == NO_SESSION


def test_a_session_without_open_entries_answers_nothing_playing(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / _CURRENT, title="It's Not Right but It's Okay", artist="Whitney Houston", bpm=129.2)
    backend = _backend(tmp_path)
    _scan(backend, root)
    database = tmp_path / "master.sqlite"
    _database(
        database,
        [(7, 1_699_000_000, -1)],
        [_row(1, start_time=1_700_000_000, end_time=1_700_000_200, name="It's Not Right but It's Okay")],
    )
    backend.serato_database_path = database

    answer = _follow(backend)

    assert answer["available"] is True
    assert answer["reason"] == "nothing_playing"
    assert answer["sessionStartedAt"] == 1_699_000_000
    assert answer["playing"] == []
    assert answer["current"] is None
    assert answer["suggestions"] == []
    assert answer["playedCount"] == 1


def test_open_entries_list_every_deck_and_the_newest_in_library_is_current(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / _CURRENT, title="It's Not Right but It's Okay", artist="Whitney Houston", bpm=129.2, key="5A")
    tagged_flac(root / _PLAYED, title="I Like It", artist="Enrique Iglesias", bpm=129.6, key="4B", energy=6)
    tagged_flac(root / "House/Plain One.flac", title="Plain One", artist="Someone", bpm=129.0, key="5A")
    backend = _backend(tmp_path)
    ids = _scan(backend, root)
    database = tmp_path / "master.sqlite"
    _database(
        database,
        [(7, 1_699_000_000, -1)],
        [
            _row(1, deck=1, start_time=1_700_000_300, name="It's Not Right but It's Okay"),
            _row(2, deck=2, start_time=1_700_000_100, name="I Like It", portable_id=_PLAYED),
        ],
    )
    backend.serato_database_path = database

    answer = _follow(backend)

    assert answer["available"] is True
    assert answer["reason"] is None
    assert answer["sessionStartedAt"] == 1_699_000_000
    assert [entry["deck"] for entry in answer["playing"]] == [1, 2]
    assert [entry["startedAt"] for entry in answer["playing"]] == [1_700_000_300, 1_700_000_100]
    assert [entry["inLibrary"] for entry in answer["playing"]] == [True, True]
    assert answer["playing"][1]["id"] == ids["I Like It"]
    assert answer["playing"][1]["title"] == "I Like It"
    assert answer["playing"][1]["artist"] == "Enrique Iglesias"
    assert answer["playing"][1]["bpm"] == 129.6
    assert answer["playing"][1]["key"] == "4B"
    assert answer["playing"][1]["energy"] == 6
    assert answer["current"]["id"] == ids["It's Not Right but It's Okay"]
    assert answer["current"]["title"] == "It's Not Right but It's Okay"
    assert [suggestion["title"] for suggestion in answer["suggestions"]] == ["Plain One"]
    assert answer["playedCount"] == 0


def test_an_open_entry_outside_the_library_carries_only_seratos_fields(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / _CURRENT, title="It's Not Right but It's Okay", artist="Whitney Houston", bpm=129.2)
    backend = _backend(tmp_path)
    _scan(backend, root)
    database = tmp_path / "master.sqlite"
    _database(
        database,
        [(7, 1_699_000_000, -1)],
        [
            _row(
                1,
                name="Unknown Song",
                artist="Unknown Artist",
                bpm=124.0,
                key="9B",
                portable_id="Other/Unknown Artist - Unknown Song.flac",
            )
        ],
    )
    backend.serato_database_path = database

    answer = _follow(backend)

    assert answer["playing"] == [
        {
            "deck": 1,
            "startedAt": 1_700_000_100,
            "inLibrary": False,
            "title": "Unknown Song",
            "artist": "Unknown Artist",
            "bpm": 124.0,
            "key": "9B",
        }
    ]
    assert answer["current"] is None
    assert answer["reason"] == "not_in_library"
    assert answer["suggestions"] == []


def test_suggestions_skip_the_session_tracks_and_other_versions_of_them(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / _CURRENT, title="It's Not Right but It's Okay", artist="Whitney Houston", bpm=129.2, key="5A")
    tagged_flac(root / _PLAYED, title="I Like It", artist="Enrique Iglesias", bpm=129.6, key="4B", energy=6)
    tagged_flac(
        root / _VERSION,
        title="It's Not Right but It's Okay (Club 69 Radio Mix)",
        artist="Whitney Houston",
        bpm=129.2,
        key="5A",
    )
    tagged_flac(root / "House/Plain One.flac", title="Plain One", artist="Someone", bpm=129.0, key="5A")
    tagged_flac(root / "House/Plain Two.flac", title="Plain Two", artist="Someone", bpm=130.0, key="5B", energy=6)
    backend = _backend(tmp_path)
    ids = _scan(backend, root)
    database = tmp_path / "master.sqlite"
    _database(
        database,
        [(7, 1_699_000_000, -1)],
        [
            _row(1, deck=1, start_time=1_700_000_300, name="It's Not Right but It's Okay"),
            _row(
                2,
                deck=2,
                start_time=1_700_000_000,
                end_time=1_700_000_200,
                name="I Like It",
                portable_id=_PLAYED,
            ),
        ],
    )
    backend.serato_database_path = database

    answer = _follow(backend)

    assert answer["current"]["id"] == ids["It's Not Right but It's Okay"]
    titles = [suggestion["title"] for suggestion in answer["suggestions"]]
    assert sorted(titles) == ["Plain One", "Plain Two"]
    assert ids["It's Not Right but It's Okay (Club 69 Radio Mix)"] not in {
        suggestion["id"] for suggestion in answer["suggestions"]
    }
    assert ids["I Like It"] not in {suggestion["id"] for suggestion in answer["suggestions"]}


def test_suggestions_are_scored_best_first_capped_at_ten_and_carry_no_path(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / _CURRENT, title="It's Not Right but It's Okay", artist="Whitney Houston", bpm=129.2, key="5A")
    for index in range(14):
        tagged_flac(
            root / f"House/Candidate {index:02d}.flac",
            title=f"Candidate {index:02d}",
            artist=f"Artist {index:02d}",
            bpm=118.0 + index,
            key=["5A", "5B", "6A", "4B", "8A"][index % 5],
            energy=3 + index % 6,
        )
    tagged_flac(root / "House/No Tempo.flac", title="No Tempo", artist="Incomplete", bpm=None)
    backend = _backend(tmp_path)
    _scan(backend, root)
    database = tmp_path / "master.sqlite"
    _database(database, [(7, 1_699_000_000, -1)], [_row(1, name="It's Not Right but It's Okay")])
    backend.serato_database_path = database

    answer = _follow(backend)
    suggestions = answer["suggestions"]

    assert answer["reason"] is None
    assert len(suggestions) == 10
    scores = [suggestion["score"] for suggestion in suggestions]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)
    assert "No Tempo" not in {suggestion["title"] for suggestion in suggestions}
    for suggestion in suggestions:
        assert set(suggestion) == {
            "id",
            "title",
            "artist",
            "bpm",
            "key",
            "energy",
            "duration",
            "genre",
            "audioFormat",
            "audioCodec",
            "bitrateKbps",
            "bitrateMode",
            "status",
            "missingFields",
            "score",
        }
    assert str(root) not in json.dumps(answer)
    assert ".flac" not in json.dumps(answer)


def test_follow_takes_no_parameters(tmp_path: Path) -> None:
    backend = _backend(tmp_path)
    with pytest.raises(BackendError) as error:
        backend.execute("live.follow", {"database": "/somewhere/master.sqlite"})

    assert error.value.code == "invalid_params"


def test_follow_leaves_the_list_in_progress_untouched(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / _CURRENT, title="It's Not Right but It's Okay", artist="Whitney Houston", bpm=129.2)
    for index in range(4):
        tagged_flac(root / f"House/Filler {index}.flac", title=f"Filler {index}", bpm=120.0 + index)
    backend = _backend(tmp_path)
    _scan(backend, root)
    database = tmp_path / "master.sqlite"
    _database(database, [(7, 1_699_000_000, -1)], [_row(1)])
    backend.serato_database_path = database
    review = backend.execute("prep.generate", {"targetTrackCount": 3})
    before = (backend.plan_id, backend.review_id, backend.review, backend.live.session, review["tracks"])

    _follow(backend)

    assert (backend.plan_id, backend.review_id, backend.review, backend.live.session, review["tracks"]) == before


def test_follow_answers_inline_while_another_job_runs(tmp_path: Path) -> None:
    assert "live.follow" in INLINE_METHODS
    root = tmp_path / "music"
    tagged_flac(root / _CURRENT, title="It's Not Right but It's Okay", artist="Whitney Houston", bpm=129.2)
    tagged_flac(root / "House/Plain One.flac", title="Plain One", artist="Someone", bpm=129.0, key="5A")
    started = threading.Event()
    release = threading.Event()

    class Backend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            if method == "prep.generate":
                started.set()
                assert release.wait(5)
                return {"blocked": True}
            return super().execute(method, params, cancellation_token=cancellation_token, progress=progress)

    backend = Backend(tmp_path / "data")
    _scan(backend, root)
    database = tmp_path / "master.sqlite"
    _database(database, [(7, 1_699_000_000, -1)], [_row(1, name="It's Not Right but It's Okay")])
    backend.serato_database_path = database
    output = io.StringIO()
    server = JsonlServer(backend, output)
    server.process_line(request("prep.generate", {"targetTrackCount": 3}))
    assert started.wait(5)
    try:
        server.process_line(request("live.follow", {}))
        answer = messages(output)[0]
        assert answer["ok"] is True
        assert answer["result"]["current"]["title"] == "It's Not Right but It's Okay"
        assert [suggestion["title"] for suggestion in answer["result"]["suggestions"]] == ["Plain One"]
    finally:
        release.set()
        server.close()
