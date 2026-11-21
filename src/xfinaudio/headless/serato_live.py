"""Read what Serato DJ plays, without ever writing to it, and match it to the library (S1, S2).

Serato DJ 5 keeps its play history in a SQLite database (``master.sqlite`` in its
library folder). XfinAudio only reads it: the database is opened through a SQLite URI
with ``mode=ro`` and a one second busy timeout, no pragma that changes the journal is
issued, the file is never copied over and only the two history tables are queried.
Serato may hold the database while it plays, so every failure — no file, a lock, an
unknown schema — is answered as "not available" with a reason instead of an exception:
the caller is a screen that asks again in a few seconds.

The snapshot covers the newest session only (highest ``id``): the open entries (an
entry with ``end_time = -1`` is a track still loaded on a deck, one per deck, newest
start first) and the entries of that session already ended, newest first, at most
``MAX_PLAYED_ENTRIES``.

The match of S2 compares an entry's ``portable_id`` — the path relative to its
volume — against the library paths: a path that ends with ``"/" + portable_id``
first exactly and then case-insensitively, then any track with the same file name.
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
    """Open the file through ``mode=ro``: reading can never create, copy or repair it."""
    uri = f"file:{quote(str(database_path))}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=BUSY_TIMEOUT_SECONDS)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {int(BUSY_TIMEOUT_SECONDS * 1000)}")
        yield connection
    finally:
        connection.close()


def _operational_reason(error: sqlite3.OperationalError) -> str:
    """Separate a database Serato holds from a schema that is not the one S1 describes."""
    if "locked" in str(error).lower() or "busy" in str(error).lower():
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
    return SeratoSnapshot(
        available=True,
        reason=None,
        session_id=session_id,
        session_started_at=_as_int(session["start_time"]),
        playing=playing,
        played=played,
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


def match_library_path(entry: SeratoEntry, library_paths: Sequence[str]) -> str | None:
    """The library path S2 matches this entry with, or ``None`` when it is not in the library."""
    portable_id = (entry.portable_id or "").strip()
    if not portable_id:
        return None
    suffix = "/" + portable_id
    for candidate in library_paths:
        if candidate.endswith(suffix):
            return candidate
    folded_suffix = suffix.casefold()
    for candidate in library_paths:
        if candidate.casefold().endswith(folded_suffix):
            return candidate
    file_name = portable_id.rsplit("/", 1)[-1]
    for candidate in library_paths:
        if candidate.rsplit("/", 1)[-1] == file_name:
            return candidate
    folded_name = file_name.casefold()
    for candidate in library_paths:
        if candidate.rsplit("/", 1)[-1].casefold() == folded_name:
            return candidate
    return None
