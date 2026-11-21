"""Read what Serato DJ plays, without ever writing to it, and match it to the library (S1, S2).

Serato DJ 5 keeps its play history in a SQLite database (``master.sqlite`` in its
library folder). XfinAudio only reads it: the database is opened through a SQLite URI
that can neither create, copy nor repair a file, no pragma that changes the journal is
issued, the file is never copied over and only the two history tables are queried.
Serato may hold the database while it plays, so every failure — no file, a lock, a
statement that runs too long, an unknown schema — is answered as "not available" with
a reason instead of an exception: the caller is a screen that asks again in a few
seconds.

Reading never leaves a file next to Serato's (S7 a). SQLite lays ``-wal`` and ``-shm``
beside a write-ahead log database the moment a read-only connection looks at its log;
Serato keeps exactly those two files while it runs, so with both of them present the
plain ``mode=ro`` read sees the log, and when they are missing the read is
``immutable=1`` and creates nothing. A rollback-journal database needs no side file
and keeps ``mode=ro``, with it the lock that answers ``serato_busy``.

One read costs at most one second in total (S7 b): a statement still running when the
budget is spent is interrupted by a progress handler and answered as ``serato_busy``.

The snapshot covers the newest session only (highest ``id``): the open entries (an
entry with ``end_time = -1`` is a track still loaded on a deck, one per deck, newest
start first) and the entries of that session already ended, newest first, at most
``MAX_PLAYED_ENTRIES``. ``last_played_id`` is the highest ``id`` among the ended ones,
counted before that cap, so a caller that keeps an answer still notices the fifty-first
ended entry (S7 c).

The match of S2 compares an entry's ``portable_id`` — the path relative to its
volume — against the library paths: a path that ends with ``"/" + portable_id``
first exactly and then case-insensitively, then any track with the same file name.
When several library tracks match in the same way, ``live.follow`` takes the one whose
BPM is closest to the BPM Serato records for that entry (S7 d).
An entry that matches nothing stays "not in the library" and carries only the title,
artist, BPM and key Serato itself records.

Nothing here writes, copies, watches or controls Serato, and no public shape carries
a file path.
"""

from __future__ import annotations

import math
import os
import sqlite3
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

if TYPE_CHECKING:
    from collections.abc import Sequence

#: Why a snapshot is not available. They match the answer contract of ``live.follow``.
SERATO_NOT_FOUND = "serato_not_found"
SERATO_BUSY = "serato_busy"
SERATO_UNREADABLE = "serato_unreadable"
NO_SESSION = "no_session"

#: An entry with this ``end_time`` is a track Serato still has loaded on a deck.
OPEN_END_TIME = -1

#: The most already-played entries of the newest session the snapshot carries.
MAX_PLAYED_ENTRIES = 50

#: Long enough for Serato to finish one statement, short enough to answer the screen.
BUSY_TIMEOUT_SECONDS = 1.0

#: One read costs at most this long in total: a statement still running is interrupted.
MAX_READ_SECONDS = 1.0

#: How many virtual machine steps pass between two looks at that budget.
PROGRESS_STEPS = 1000

#: The first sixteen bytes of every SQLite database file.
_SQLITE_HEADER = b"SQLite format 3\x00"

_ENTRY_COLUMNS = "deck, start_time, end_time, name, artist, bpm, key, portable_id"


def default_database_path() -> Path:
    """The ``master.sqlite`` Serato DJ 5 keeps its history in on this platform."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "Serato" / "Library" / "master.sqlite"
    return Path.home() / "Library" / "Application Support" / "Serato" / "Library" / "master.sqlite"


@dataclass(frozen=True)
class SeratoEntry:
    """One row of Serato's ``history_entry``, already decoded."""

    deck: int
    session_id: int
    start_time: int
    end_time: int
    title: str | None
    artist: str | None
    bpm: float | None
    key: str | None
    portable_id: str | None

    @property
    def is_open(self) -> bool:
        """True while Serato has the track loaded on its deck."""
        return self.end_time == OPEN_END_TIME

    def public(self) -> dict[str, Any]:
        """The fields a review or a screen shows; the relative path stays inside."""
        return {
            "deck": self.deck,
            "startedAt": self.start_time,
            "title": self.title,
            "artist": self.artist,
            "bpm": self.bpm,
            "key": self.key,
        }


@dataclass(frozen=True)
class SeratoSnapshot:
    """What Serato plays now, or why it cannot be read."""

    available: bool
    reason: str | None
    session_id: int | None
    session_started_at: int | None
    playing: tuple[SeratoEntry, ...]
    played: tuple[SeratoEntry, ...]
    #: The highest ``id`` among the newest session's ended entries, before the cap at
    #: ``MAX_PLAYED_ENTRIES``: what tells a kept answer a further entry ended (S7 c).
    last_played_id: int | None = None

    @classmethod
    def unavailable(cls, reason: str) -> SeratoSnapshot:
        """A snapshot that answers "not available" with the reason and nothing else."""
        return cls(
            available=False,
            reason=reason,
            session_id=None,
            session_started_at=None,
            playing=(),
            played=(),
        )

    def public(self) -> dict[str, Any]:
        """The snapshot as the answer of a read-only method; never a file path."""
        return {
            "available": self.available,
            "reason": self.reason,
            "sessionStartedAt": self.session_started_at,
            "playing": [entry.public() for entry in self.playing],
            "played": [entry.public() for entry in self.played],
        }


def read_serato_snapshot(database_path: Path | str | None = None) -> SeratoSnapshot:
    """Read the newest Serato session, read-only, answering "not available" instead of raising."""
    path = Path(database_path) if database_path is not None else default_database_path()
    if not path.is_file():
        return SeratoSnapshot.unavailable(SERATO_NOT_FOUND)
    try:
        with _read_only_connection(path) as connection:
            return _read_snapshot(connection)
    except sqlite3.OperationalError as error:
        return SeratoSnapshot.unavailable(_operational_reason(error))
    except sqlite3.Error:
        return SeratoSnapshot.unavailable(SERATO_UNREADABLE)
    except OSError:
        return SeratoSnapshot.unavailable(SERATO_NOT_FOUND)


@contextmanager
def _read_only_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Open the file so that reading it creates, copies and repairs nothing, for one second."""
    connection = sqlite3.connect(_read_only_uri(database_path), uri=True, timeout=BUSY_TIMEOUT_SECONDS)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(BUSY_TIMEOUT_SECONDS * 1000)}")
        deadline = time.monotonic() + MAX_READ_SECONDS

        def interrupt() -> int:
            return 1 if time.monotonic() > deadline else 0

        connection.set_progress_handler(interrupt, PROGRESS_STEPS)
        yield connection
    finally:
        connection.set_progress_handler(None, 0)
        connection.close()


def _read_only_uri(database_path: Path) -> str:
    """``mode=ro`` where a read cannot create a file, ``immutable=1`` where it could (S7 a).

    SQLite lays ``-wal`` and ``-shm`` beside a write-ahead log database as soon as a
    read-only connection looks at its log. Those two files are exactly what Serato keeps
    while it runs, so with both of them present ``mode=ro`` reads the log and honours
    its lock. With them missing Serato is not writing that log and the file is read
    ``immutable=1``, which creates nothing. A rollback-journal database needs no side
    file at all, so it keeps ``mode=ro`` and the lock that answers ``serato_busy``.
    """
    uri = f"file:{quote(str(database_path))}?mode=ro"
    if not _is_write_ahead_log(database_path):
        return uri
    side_files = (
        database_path.with_name(database_path.name + "-wal"),
        database_path.with_name(database_path.name + "-shm"),
    )
    if all(side_file.is_file() for side_file in side_files):
        return uri
    return uri + "&immutable=1"


def _is_write_ahead_log(database_path: Path) -> bool:
    """True when the file's own header says its journal is the write-ahead log."""
    try:
        with database_path.open("rb") as header:
            first = header.read(20)
    except OSError:
        return False
    # Byte 18 is the file format write version, and 2 marks the write-ahead log.
    return len(first) == 20 and first[:16] == _SQLITE_HEADER and first[18] == 2


def _operational_reason(error: sqlite3.OperationalError) -> str:
    """Separate a database Serato holds, or a statement cut short, from a different schema."""
    message = str(error).lower()
    if "locked" in message or "busy" in message or "interrupt" in message:
        return SERATO_BUSY
    return SERATO_UNREADABLE


def _read_snapshot(connection: sqlite3.Connection) -> SeratoSnapshot:
    """Query only the two history tables, and only the newest session."""
    session = connection.execute(
        "SELECT id, start_time FROM history_session ORDER BY id DESC LIMIT 1",
    ).fetchone()
    if session is None:
        return SeratoSnapshot.unavailable(NO_SESSION)
    session_id = int(session["id"])
    playing = _open_entries(connection, session_id)
    rows = connection.execute(
        f"SELECT {_ENTRY_COLUMNS} FROM history_entry "
        "WHERE session_id = ? AND end_time != ? ORDER BY start_time DESC, id DESC LIMIT ?",
        (session_id, OPEN_END_TIME, MAX_PLAYED_ENTRIES),
    ).fetchall()
    played = tuple(_entry(row, session_id) for row in rows)
    last_played_id = _as_int(
        connection.execute(
            "SELECT MAX(id) FROM history_entry WHERE session_id = ? AND end_time != ?",
            (session_id, OPEN_END_TIME),
        ).fetchone()[0]
    )
    return SeratoSnapshot(
        available=True,
        reason=None,
        session_id=session_id,
        session_started_at=_as_int(session["start_time"]),
        playing=playing,
        played=played,
        last_played_id=last_played_id,
    )


def _open_entries(connection: sqlite3.Connection, session_id: int) -> tuple[SeratoEntry, ...]:
    """One open entry per deck, the newest start first."""
    rows = connection.execute(
        f"SELECT {_ENTRY_COLUMNS} FROM history_entry "
        "WHERE session_id = ? AND end_time = ? ORDER BY start_time DESC, id DESC",
        (session_id, OPEN_END_TIME),
    ).fetchall()
    seen: set[int] = set()
    open_entries: list[SeratoEntry] = []
    for row in rows:
        entry = _entry(row, session_id)
        if entry.deck in seen:
            continue
        seen.add(entry.deck)
        open_entries.append(entry)
    return tuple(open_entries)


def _entry(row: sqlite3.Row, session_id: int) -> SeratoEntry:
    end_time = _as_int(row["end_time"])
    return SeratoEntry(
        deck=_as_int(row["deck"]) or 0,
        session_id=session_id,
        start_time=_as_int(row["start_time"]) or 0,
        end_time=OPEN_END_TIME if end_time is None else end_time,
        title=_as_text(row["name"]),
        artist=_as_text(row["artist"]),
        bpm=_as_float(row["bpm"]),
        key=_as_text(row["key"]),
        portable_id=_as_text(row["portable_id"]),
    )


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def match_library_paths(entry: SeratoEntry, library_paths: Sequence[str]) -> tuple[str, ...]:
    """Every library path S2 matches this entry with, from the first way that matches any.

    The ways keep their precedence — path suffix before file name — and inside one way
    every match is returned, so the caller can prefer the track closest in BPM (S7 d).
    """
    portable_id = (entry.portable_id or "").strip()
    if not portable_id:
        return ()
    suffix = "/" + portable_id
    folded_suffix = suffix.casefold()
    file_name = portable_id.rsplit("/", 1)[-1]
    folded_name = file_name.casefold()
    ways = (
        lambda candidate: candidate.endswith(suffix),
        lambda candidate: candidate.casefold().endswith(folded_suffix),
        lambda candidate: _file_name(candidate) == file_name,
        lambda candidate: _file_name(candidate).casefold() == folded_name,
    )
    for matches in ways:
        found = tuple(candidate for candidate in library_paths if matches(candidate))
        if found:
            return found
    return ()


def match_library_path(entry: SeratoEntry, library_paths: Sequence[str]) -> str | None:
    """The library path S2 matches this entry with, or ``None`` when it is not in the library."""
    matched = match_library_paths(entry, library_paths)
    return matched[0] if matched else None


def _file_name(path: str) -> str:
    return path.rsplit("/", 1)[-1]
