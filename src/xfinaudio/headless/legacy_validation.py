"""Validate current legacy schemas and rebuild quarantined app-owned data only."""

from __future__ import annotations

import math
import sqlite3
import time
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from xfinaudio.headless.legacy_source import invalid
from xfinaudio.library.playlist_models import Playlist
from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.track_repository import SCHEMA_VERSION, TrackRepository

MAX_TRACKS, MAX_PLAYLISTS, MAX_REFERENCES = 100000, 5000, 250000
AUDIO_COLUMNS = {"audio_format", "audio_codec", "bitrate_kbps", "bitrate_mode"}
PROFILE_FIELDS = (
    "spectral_profile",
    "danceability_profile",
    "edge_spectral_profile",
    "tonal_profile",
    "loudness_profile",
)


@contextmanager
def memory_database(content: bytes):
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(content)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA query_only=ON")
        deadline = time.monotonic() + 15
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise invalid()
        yield connection
    finally:
        connection.close()


def validate_schema(
    source: sqlite3.Connection, target: sqlite3.Connection, tables: set[str], version: int | tuple[int, ...]
) -> None:
    source_version = source.execute("PRAGMA user_version").fetchone()[0]
    if source_version not in ((version,) if isinstance(version, int) else version):
        raise invalid()
    objects = source.execute("SELECT type,name,tbl_name,sql FROM sqlite_master").fetchall()
    if {row["name"] for row in objects if row["type"] == "table"} != tables:
        raise invalid()
    permitted = {(row[0], row[1], row[2]) for row in target.execute("SELECT type,name,tbl_name FROM sqlite_master")}
    if any((row["type"], row["name"], row["tbl_name"]) not in permitted for row in objects):
        raise invalid()
    for table in tables:
        # Table names come solely from constant sets, never SQL or user data.
        columns = [tuple(row) for row in source.execute(f"PRAGMA table_info({table})")]
        expected = [tuple(row) for row in target.execute(f"PRAGMA table_info({table})")]
        if table == "tracks":
            absent = (AUDIO_COLUMNS if source_version < 7 else set()) | (
                {"tonal_profile_json"} if source_version < 6 else set()
            )
            # Additive migrations append columns. Verify definitions by name, not physical order.
            if {row[1]: row[2:] for row in columns} != {row[1]: row[2:] for row in expected if row[1] not in absent}:
                raise invalid()
        elif columns != expected:
            raise invalid()


def valid_path(value: Any) -> None:
    if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
        raise invalid()
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or str(path) != value or value.startswith("//"):
        raise invalid()
    # Deliberately lexical: imported paths confer no permission to stat/read audio.


def bounded_rows(connection: sqlite3.Connection, table: str, limit: int) -> list[sqlite3.Row]:
    if connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] > limit:
        raise invalid()
    rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    for row in rows:
        for value in row:
            if isinstance(value, (bytes, float)) and (isinstance(value, bytes) or not math.isfinite(value)):
                raise invalid()
            if isinstance(value, str) and len(value) > 256 * 1024:
                raise invalid()
    return rows


def rebuild_tracks(content: bytes | None) -> tuple[bytes, int, int]:
    with closing(sqlite3.connect(":memory:")) as target:
        TrackRepository._ensure_schema(target)
        target.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        rows, cached = [], 0
        if content is not None:
            with memory_database(content) as source:
                validate_schema(source, target, {"tracks"}, (5, 6, 7))
                rows = bounded_rows(source, "tracks", MAX_TRACKS)
                for row in rows:
                    valid_path(row["path"])
                    values = {**dict.fromkeys(AUDIO_COLUMNS | {"tonal_profile_json"}), **dict(row)}
                    record = TrackRepository._row_to_record(values)
                    if any(
                        values.get(field + "_json") is not None and getattr(record, field) is None
                        for field in PROFILE_FIELDS
                    ):
                        raise invalid()
                    for field in ("file_mtime_ns", "file_size_bytes"):
                        if row[field] is not None and (type(row[field]) is not int or row[field] < 0):
                            raise invalid()
                    cached += any(getattr(record, field) is not None for field in PROFILE_FIELDS)
                    # Column identifiers have already passed the exact schema allowlist.
                    target.execute(
                        "INSERT INTO tracks (" + ",".join(row.keys()) + ") VALUES (" + ",".join("?" for _ in row) + ")",
                        tuple(row),
                    )
        target.commit()
        return target.serialize(), len(rows), cached


def rebuild_playlists(content: bytes | None) -> tuple[bytes, int, int, list[str]]:
    with closing(sqlite3.connect(":memory:")) as target:
        PlaylistRepository._ensure_schema(target)
        playlists, references = [], []
        if content is not None:
            with memory_database(content) as source:
                validate_schema(source, target, {"playlists", "playlist_tracks", "sqlite_sequence"}, 0)
                playlists = bounded_rows(source, "playlists", MAX_PLAYLISTS)
                references = bounded_rows(source, "playlist_tracks", MAX_REFERENCES)
                ids = set()
                for row in playlists:
                    if (
                        type(row["id"]) is not int
                        or row["id"] < 1
                        or not isinstance(row["name"], str)
                        or not row["name"].strip()
                        or len(row["name"]) > 200
                    ):
                        raise invalid()
                    Playlist(
                        row["id"],
                        row["name"],
                        datetime.fromisoformat(row["created_at"]),
                        datetime.fromisoformat(row["updated_at"]),
                        [],
                    )
                    ids.add(row["id"])
                    target.execute("INSERT INTO playlists VALUES (?,?,?,?)", tuple(row))
                positions: dict[int, list[int]] = {}
                for row in references:
                    valid_path(row["track_path"])
                    if row["playlist_id"] not in ids or type(row["position"]) is not int or row["position"] < 0:
                        raise invalid()
                    positions.setdefault(row["playlist_id"], []).append(row["position"])
                    target.execute("INSERT INTO playlist_tracks VALUES (?,?,?)", tuple(row))
                if any(sorted(values) != list(range(len(values))) for values in positions.values()):
                    raise invalid()
        names = ["".join(character for character in row["name"] if character.isprintable()) for row in playlists[:20]]
        target.commit()
        return target.serialize(), len(playlists), len(references), names
