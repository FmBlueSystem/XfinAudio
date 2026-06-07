"""SQLite persistence for scanned track records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from xfinaudio.library.models import TrackRecord

SCHEMA_VERSION = 1


class DatabaseSchemaError(RuntimeError):
    """Base error for unsupported or unsafe SQLite schema states."""


class UnsupportedDatabaseVersionError(DatabaseSchemaError):
    """Raised when a database was created by a newer unsupported schema."""


class TrackRepository:
    """Persist scanned track metadata in an application-owned SQLite database."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._initialize()

    def save_scan_results(self, records: Iterable[TrackRecord]) -> None:
        """Upsert scanned track records by absolute file path."""
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO tracks (
                    path, title, artist, bpm, camelot_key, energy_level, genre, tags_json,
                    metadata_status, missing_required_fields_json, source_fields_json, raw_metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title = excluded.title,
                    artist = excluded.artist,
                    bpm = excluded.bpm,
                    camelot_key = excluded.camelot_key,
                    energy_level = excluded.energy_level,
                    genre = excluded.genre,
                    tags_json = excluded.tags_json,
                    metadata_status = excluded.metadata_status,
                    missing_required_fields_json = excluded.missing_required_fields_json,
                    source_fields_json = excluded.source_fields_json,
                    raw_metadata_json = excluded.raw_metadata_json
                """,
                [self._record_to_row(record) for record in records],
            )

    def list_tracks(self) -> list[TrackRecord]:
        """Return persisted tracks ordered deterministically by path."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT path, title, artist, bpm, camelot_key, energy_level, genre, tags_json,
                       metadata_status, missing_required_fields_json, source_fields_json, raw_metadata_json
                FROM tracks
                ORDER BY path
                """
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_display_tracks(self) -> list[TrackRecord]:
        """Return persisted tracks for UI display without loading large raw metadata blobs."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT path, title, artist, bpm, camelot_key, energy_level, genre, tags_json,
                       metadata_status, missing_required_fields_json
                FROM tracks
                ORDER BY path
                """
            ).fetchall()
        return [self._display_row_to_record(row) for row in rows]

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
            if schema_version > SCHEMA_VERSION:
                raise UnsupportedDatabaseVersionError(
                    f"Unsupported database schema version {schema_version}; "
                    f"current application supports {SCHEMA_VERSION}"
                )
            if schema_version == 0 and self._tracks_table_exists(connection):
                raise DatabaseSchemaError(
                    "Unversioned database contains an existing tracks table; "
                    "refusing to mark it as schema v1 without an explicit migration"
                )
            self._ensure_schema(connection)
            if schema_version == 0:
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def _tracks_table_exists(connection: sqlite3.Connection) -> bool:
        row = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'tracks'").fetchone()
        return row is not None

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                path TEXT PRIMARY KEY,
                title TEXT,
                artist TEXT,
                bpm REAL,
                camelot_key TEXT,
                energy_level INTEGER,
                genre TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_status TEXT NOT NULL CHECK(metadata_status IN ('complete', 'incomplete')),
                missing_required_fields_json TEXT NOT NULL DEFAULT '[]',
                source_fields_json TEXT NOT NULL DEFAULT '{}',
                raw_metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tracks_metadata_status ON tracks (metadata_status)")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _record_to_row(record: TrackRecord) -> tuple[Any, ...]:
        return (
            record.path,
            record.title,
            record.artist,
            record.bpm,
            record.camelot_key,
            record.energy_level,
            record.genre,
            json.dumps(record.tags, sort_keys=True),
            record.metadata_status,
            json.dumps(record.missing_required_fields, sort_keys=True),
            json.dumps(record.source_fields, sort_keys=True),
            json.dumps(record.raw_metadata, sort_keys=True),
        )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> TrackRecord:
        return TrackRecord(
            path=row["path"],
            title=row["title"],
            artist=row["artist"],
            bpm=row["bpm"],
            camelot_key=row["camelot_key"],
            energy_level=row["energy_level"],
            genre=row["genre"],
            tags=json.loads(row["tags_json"]),
            metadata_status=row["metadata_status"],
            missing_required_fields=json.loads(row["missing_required_fields_json"]),
            source_fields=json.loads(row["source_fields_json"]),
            raw_metadata=json.loads(row["raw_metadata_json"]),
        )

    @staticmethod
    def _display_row_to_record(row: sqlite3.Row) -> TrackRecord:
        return TrackRecord(
            path=row["path"],
            title=row["title"],
            artist=row["artist"],
            bpm=row["bpm"],
            camelot_key=row["camelot_key"],
            energy_level=row["energy_level"],
            genre=row["genre"],
            tags=json.loads(row["tags_json"]),
            metadata_status=row["metadata_status"],
            missing_required_fields=json.loads(row["missing_required_fields_json"]),
        )
