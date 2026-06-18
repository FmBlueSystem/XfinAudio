"""SQLite persistence for scanned track records."""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.genre.models import GenreDecision
from xfinaudio.library.models import TrackRecord

SCHEMA_VERSION = 4


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
                    path, title, artist, bpm, camelot_key, energy_level, duration, genre, tags_json,
                    metadata_status, missing_required_fields_json, source_fields_json, raw_metadata_json,
                    spectral_profile_json, genre_decision_json,
                    file_mtime_ns, file_size_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title = excluded.title,
                    artist = excluded.artist,
                    bpm = excluded.bpm,
                    camelot_key = excluded.camelot_key,
                    energy_level = excluded.energy_level,
                    duration = excluded.duration,
                    genre = excluded.genre,
                    tags_json = excluded.tags_json,
                    metadata_status = excluded.metadata_status,
                    missing_required_fields_json = excluded.missing_required_fields_json,
                    source_fields_json = excluded.source_fields_json,
                    raw_metadata_json = excluded.raw_metadata_json,
                    spectral_profile_json = excluded.spectral_profile_json,
                    genre_decision_json = excluded.genre_decision_json,
                    file_mtime_ns = excluded.file_mtime_ns,
                    file_size_bytes = excluded.file_size_bytes
                """,
                [self._record_to_row(record) for record in records],
            )

    def list_tracks(self) -> list[TrackRecord]:
        """Return persisted tracks ordered deterministically by path."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT path, title, artist, bpm, camelot_key, energy_level, duration, genre, tags_json,
                       metadata_status, missing_required_fields_json, source_fields_json, raw_metadata_json,
                       spectral_profile_json, genre_decision_json
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
                SELECT path, title, artist, bpm, camelot_key, energy_level, duration, genre, tags_json,
                       metadata_status, missing_required_fields_json, spectral_profile_json, genre_decision_json
                FROM tracks
                ORDER BY path
                """
            ).fetchall()
        return [self._display_row_to_record(row) for row in rows]

    def update_spectral_profile(
        self,
        path: str,
        profile: SpectralProfile,
    ) -> bool:
        """Persist a spectral profile for a single track, updating file identity fields.

        Returns ``True`` if the track existed and was updated.
        """
        mtime_ns: int | None = None
        size_bytes: int | None = None
        try:
            stat = Path(path).stat()
            mtime_ns = stat.st_mtime_ns
            size_bytes = stat.st_size
        except OSError:
            pass
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tracks
                SET spectral_profile_json = ?,
                    file_mtime_ns = ?,
                    file_size_bytes = ?
                WHERE path = ?
                """,
                (_serialize_profile(profile), mtime_ns, size_bytes, path),
            )
            return cursor.rowcount > 0

    def load_spectral_profile_cache(
        self,
        paths: Iterable[str],
    ) -> dict[str, tuple[int, int, SpectralProfile]]:
        """Return cached spectral profiles whose file identity fields are present.

        The returned mapping is ``path -> (mtime_ns, size_bytes, profile)`` and is
        suitable for passing to the batch analyzer's cache.
        """
        path_list = list(paths)
        if not path_list:
            return {}
        placeholders = ",".join("?" * len(path_list))
        query = f"""
            SELECT path, file_mtime_ns, file_size_bytes, spectral_profile_json
            FROM tracks
            WHERE path IN ({placeholders})
              AND file_mtime_ns IS NOT NULL
              AND file_size_bytes IS NOT NULL
              AND spectral_profile_json IS NOT NULL
        """
        cache: dict[str, tuple[int, int, SpectralProfile]] = {}
        with self._connect() as connection:
            rows = connection.execute(query, path_list).fetchall()
        for row in rows:
            profile = _deserialize_profile(row["spectral_profile_json"])
            if profile is not None:
                cache[row["path"]] = (row["file_mtime_ns"], row["file_size_bytes"], profile)
        return cache

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
            if schema_version < SCHEMA_VERSION:
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
                duration REAL,
                genre TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_status TEXT NOT NULL CHECK(metadata_status IN ('complete', 'incomplete')),
                missing_required_fields_json TEXT NOT NULL DEFAULT '[]',
                source_fields_json TEXT NOT NULL DEFAULT '{}',
                raw_metadata_json TEXT NOT NULL DEFAULT '{}',
                spectral_profile_json TEXT,
                file_mtime_ns INTEGER,
                file_size_bytes INTEGER
            )
            """
        )
        # Gracefully add columns introduced after the initial schema
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN duration REAL")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN spectral_profile_json TEXT")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN file_mtime_ns INTEGER")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN file_size_bytes INTEGER")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN genre_decision_json TEXT")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tracks_metadata_status ON tracks (metadata_status)")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _record_to_row(record: TrackRecord) -> tuple[Any, ...]:
        mtime_ns: int | None = None
        size_bytes: int | None = None
        try:
            stat = Path(record.path).stat()
            mtime_ns = stat.st_mtime_ns
            size_bytes = stat.st_size
        except OSError:
            pass
        return (
            record.path,
            record.title,
            record.artist,
            record.bpm,
            record.camelot_key,
            record.energy_level,
            record.duration,
            record.genre,
            json.dumps(record.tags, sort_keys=True),
            record.metadata_status,
            json.dumps(record.missing_required_fields, sort_keys=True),
            json.dumps(record.source_fields, sort_keys=True),
            json.dumps(record.raw_metadata, sort_keys=True),
            _serialize_profile(record.spectral_profile),
            _serialize_decision(record.genre_decision),
            mtime_ns,
            size_bytes,
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
            duration=row["duration"],
            genre=row["genre"],
            tags=json.loads(row["tags_json"]),
            metadata_status=row["metadata_status"],
            missing_required_fields=json.loads(row["missing_required_fields_json"]),
            source_fields=json.loads(row["source_fields_json"]),
            raw_metadata=json.loads(row["raw_metadata_json"]),
            spectral_profile=_deserialize_profile(row["spectral_profile_json"]),
            genre_decision=_deserialize_decision(row["genre_decision_json"]),
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
            duration=row["duration"],
            genre=row["genre"],
            tags=json.loads(row["tags_json"]),
            metadata_status=row["metadata_status"],
            missing_required_fields=json.loads(row["missing_required_fields_json"]),
            spectral_profile=_deserialize_profile(row["spectral_profile_json"]),
            genre_decision=_deserialize_decision(row["genre_decision_json"]),
        )


def _serialize_profile(profile: SpectralProfile | None) -> str | None:
    if profile is None:
        return None
    return profile.model_dump_json()


def _deserialize_profile(value: str | None) -> SpectralProfile | None:
    if value is None:
        return None
    try:
        return SpectralProfile.model_validate_json(value)
    except Exception:
        return None


def _serialize_decision(decision: GenreDecision | None) -> str | None:
    if decision is None:
        return None
    return decision.model_dump_json()


def _deserialize_decision(value: str | None) -> GenreDecision | None:
    if value is None:
        return None
    try:
        return GenreDecision.model_validate_json(value)
    except Exception:
        return None
