"""SQLite persistence for scanned track records."""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from xfinaudio.audio.danceability import (
    CURRENT_DANCEABILITY_VERSION,
    DanceabilityProfile,
)
from xfinaudio.audio.spectral_profile import (
    CURRENT_ANALYSIS_VERSION,
    CURRENT_EDGE_ANALYSIS_VERSION,
    EdgeSpectralProfile,
    SpectralProfile,
    dominant_color_for_ratios,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.mixedinkey_contract import PARSED_TAG_KEYS

SCHEMA_VERSION = 4

# Bound placeholders per IN (...) clause. Modern SQLite allows 32766, older
# builds only 999; 900 stays safe everywhere and keeps queries small.
_MAX_QUERY_VARIABLES = 900


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
            # Energy cues are cheap tag-derived values, so a rescan replaces
            # them directly rather than preserving stale values like a profile.
            # The mtime branch alone discarded 1,266 byte-identical files on a
            # real re-scan, so prefer the FLAC audio checksum when available.
            connection.executemany(
                """
                INSERT INTO tracks (
                    path, title, artist, bpm, camelot_key, energy_level,
                    energy_in, energy_out, energy_peak, duration, genre, tags_json,
                    metadata_status, missing_required_fields_json, source_fields_json, raw_metadata_json,
                    audio_md5, spectral_profile_json, danceability_profile_json,
                    edge_spectral_profile_json, file_mtime_ns, file_size_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title = excluded.title,
                    artist = excluded.artist,
                    bpm = excluded.bpm,
                    camelot_key = excluded.camelot_key,
                    energy_level = excluded.energy_level,
                    energy_in = excluded.energy_in,
                    energy_out = excluded.energy_out,
                    energy_peak = excluded.energy_peak,
                    duration = excluded.duration,
                    genre = excluded.genre,
                    tags_json = excluded.tags_json,
                    metadata_status = excluded.metadata_status,
                    missing_required_fields_json = excluded.missing_required_fields_json,
                    source_fields_json = excluded.source_fields_json,
                    raw_metadata_json = excluded.raw_metadata_json,
                    audio_md5 = excluded.audio_md5,
                    spectral_profile_json = CASE
                        WHEN excluded.spectral_profile_json IS NOT NULL THEN excluded.spectral_profile_json
                        WHEN tracks.audio_md5 IS NOT NULL
                             AND tracks.audio_md5 = excluded.audio_md5
                            THEN tracks.spectral_profile_json
                        WHEN tracks.file_mtime_ns = excluded.file_mtime_ns
                             AND tracks.file_size_bytes = excluded.file_size_bytes
                            THEN tracks.spectral_profile_json
                        ELSE NULL
                    END,
                    danceability_profile_json = CASE
                        WHEN excluded.danceability_profile_json IS NOT NULL
                            THEN excluded.danceability_profile_json
                        WHEN tracks.audio_md5 IS NOT NULL
                             AND tracks.audio_md5 = excluded.audio_md5
                            THEN tracks.danceability_profile_json
                        WHEN tracks.file_mtime_ns = excluded.file_mtime_ns
                             AND tracks.file_size_bytes = excluded.file_size_bytes
                            THEN tracks.danceability_profile_json
                        ELSE NULL
                    END,
                    edge_spectral_profile_json = CASE
                        WHEN excluded.edge_spectral_profile_json IS NOT NULL
                            THEN excluded.edge_spectral_profile_json
                        WHEN tracks.audio_md5 IS NOT NULL
                             AND tracks.audio_md5 = excluded.audio_md5
                            THEN tracks.edge_spectral_profile_json
                        WHEN tracks.file_mtime_ns = excluded.file_mtime_ns
                             AND tracks.file_size_bytes = excluded.file_size_bytes
                            THEN tracks.edge_spectral_profile_json
                        ELSE NULL
                    END,
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
                SELECT path, title, artist, bpm, camelot_key, energy_level,
                       energy_in, energy_out, energy_peak, duration, genre, tags_json,
                       metadata_status, missing_required_fields_json, source_fields_json, raw_metadata_json,
                       audio_md5, spectral_profile_json, danceability_profile_json,
                       edge_spectral_profile_json
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
                SELECT path, title, artist, bpm, camelot_key, energy_level,
                       energy_in, energy_out, energy_peak, duration, genre, tags_json,
                       metadata_status, missing_required_fields_json, spectral_profile_json,
                       danceability_profile_json, edge_spectral_profile_json, audio_md5
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
        cache: dict[str, tuple[int, int, SpectralProfile]] = {}
        with self._connect() as connection:
            for start in range(0, len(path_list), _MAX_QUERY_VARIABLES):
                chunk = path_list[start : start + _MAX_QUERY_VARIABLES]
                placeholders = ",".join("?" * len(chunk))
                query = f"""
                    SELECT path, file_mtime_ns, file_size_bytes, spectral_profile_json
                    FROM tracks
                    WHERE path IN ({placeholders})
                      AND file_mtime_ns IS NOT NULL
                      AND file_size_bytes IS NOT NULL
                      AND spectral_profile_json IS NOT NULL
                """
                for row in connection.execute(query, chunk):
                    profile = _deserialize_profile(row["spectral_profile_json"])
                    if profile is not None and profile.analysis_version == CURRENT_ANALYSIS_VERSION:
                        cache[row["path"]] = (row["file_mtime_ns"], row["file_size_bytes"], profile)
        return cache

    def update_danceability_profile(
        self,
        path: str,
        profile: DanceabilityProfile,
    ) -> bool:
        """Persist a danceability profile for a track and refresh its file identity."""
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
                SET danceability_profile_json = ?,
                    file_mtime_ns = ?,
                    file_size_bytes = ?
                WHERE path = ?
                """,
                (_serialize_danceability_profile(profile), mtime_ns, size_bytes, path),
            )
            return cursor.rowcount > 0

    def load_danceability_profile_cache(
        self,
        paths: Iterable[str],
    ) -> dict[str, tuple[int, int, DanceabilityProfile]]:
        """Return current cached danceability profiles with file identity."""
        path_list = list(paths)
        if not path_list:
            return {}
        cache: dict[str, tuple[int, int, DanceabilityProfile]] = {}
        with self._connect() as connection:
            for start in range(0, len(path_list), _MAX_QUERY_VARIABLES):
                chunk = path_list[start : start + _MAX_QUERY_VARIABLES]
                placeholders = ",".join("?" * len(chunk))
                query = f"""
                    SELECT path, file_mtime_ns, file_size_bytes, danceability_profile_json
                    FROM tracks
                    WHERE path IN ({placeholders})
                      AND file_mtime_ns IS NOT NULL
                      AND file_size_bytes IS NOT NULL
                      AND danceability_profile_json IS NOT NULL
                """
                for row in connection.execute(query, chunk):
                    profile = _deserialize_danceability_profile(row["danceability_profile_json"])
                    if profile is not None and profile.analysis_version == CURRENT_DANCEABILITY_VERSION:
                        cache[row["path"]] = (row["file_mtime_ns"], row["file_size_bytes"], profile)
        return cache

    def update_edge_spectral_profile(
        self,
        path: str,
        profile: EdgeSpectralProfile,
    ) -> bool:
        """Persist an edge spectral profile and refresh its file identity."""
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
                SET edge_spectral_profile_json = ?,
                    file_mtime_ns = ?,
                    file_size_bytes = ?
                WHERE path = ?
                """,
                (_serialize_edge_spectral_profile(profile), mtime_ns, size_bytes, path),
            )
            return cursor.rowcount > 0

    def load_edge_spectral_profile_cache(
        self,
        paths: Iterable[str],
    ) -> dict[str, tuple[int, int, EdgeSpectralProfile]]:
        """Return current cached edge spectral profiles with file identity."""
        path_list = list(paths)
        if not path_list:
            return {}
        cache: dict[str, tuple[int, int, EdgeSpectralProfile]] = {}
        with self._connect() as connection:
            for start in range(0, len(path_list), _MAX_QUERY_VARIABLES):
                chunk = path_list[start : start + _MAX_QUERY_VARIABLES]
                placeholders = ",".join("?" * len(chunk))
                query = f"""
                    SELECT path, file_mtime_ns, file_size_bytes, edge_spectral_profile_json
                    FROM tracks
                    WHERE path IN ({placeholders})
                      AND file_mtime_ns IS NOT NULL
                      AND file_size_bytes IS NOT NULL
                      AND edge_spectral_profile_json IS NOT NULL
                """
                for row in connection.execute(query, chunk):
                    profile = _deserialize_edge_spectral_profile(row["edge_spectral_profile_json"])
                    if profile is not None and profile.analysis_version == CURRENT_EDGE_ANALYSIS_VERSION:
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
            needs_raw_metadata_trim = 0 < schema_version < 4
            if needs_raw_metadata_trim:
                self._trim_legacy_raw_metadata(connection)
            if schema_version < SCHEMA_VERSION:
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        if needs_raw_metadata_trim:
            self._reclaim_free_pages()

    @staticmethod
    def _trim_legacy_raw_metadata(connection: sqlite3.Connection) -> None:
        """Drop tag keys the parser never reads from already-persisted rows.

        Schema v4 stopped writing them (see library/scan_service.py), but existing
        databases still carry them: 261 MB of 269 MB on a real 10,392-track library,
        dominated by Serato overviews and Mixed In Key beatgrids. Trimming here makes
        an upgraded database equivalent to a freshly scanned one.
        """
        updates: list[tuple[str, str]] = []
        for path, raw_json in connection.execute("SELECT path, raw_metadata_json FROM tracks"):
            try:
                raw = json.loads(raw_json)
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(raw, dict):
                continue
            trimmed = {key: value for key, value in raw.items() if key.casefold() in PARSED_TAG_KEYS}
            if len(trimmed) != len(raw):
                updates.append((json.dumps(trimmed, sort_keys=True), path))
        connection.executemany("UPDATE tracks SET raw_metadata_json = ? WHERE path = ?", updates)

    def _reclaim_free_pages(self) -> None:
        """VACUUM so the trimmed payload is returned to the filesystem.

        Must run outside the migration transaction; without it SQLite keeps the
        freed pages and the file never shrinks.
        """
        connection = self._connect()
        try:
            connection.execute("VACUUM")
        finally:
            connection.close()

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
                energy_in INTEGER,
                energy_out INTEGER,
                energy_peak INTEGER,
                duration REAL,
                genre TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_status TEXT NOT NULL CHECK(metadata_status IN ('complete', 'incomplete')),
                missing_required_fields_json TEXT NOT NULL DEFAULT '[]',
                source_fields_json TEXT NOT NULL DEFAULT '{}',
                raw_metadata_json TEXT NOT NULL DEFAULT '{}',
                audio_md5 TEXT,
                spectral_profile_json TEXT,
                danceability_profile_json TEXT,
                edge_spectral_profile_json TEXT,
                file_mtime_ns INTEGER,
                file_size_bytes INTEGER
            )
            """
        )
        # Gracefully add columns introduced after the initial schema
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN duration REAL")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN energy_in INTEGER")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN energy_out INTEGER")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN energy_peak INTEGER")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN spectral_profile_json TEXT")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN danceability_profile_json TEXT")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN edge_spectral_profile_json TEXT")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN file_mtime_ns INTEGER")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN file_size_bytes INTEGER")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("ALTER TABLE tracks ADD COLUMN audio_md5 TEXT")
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
            record.energy_in,
            record.energy_out,
            record.energy_peak,
            record.duration,
            record.genre,
            json.dumps(record.tags, sort_keys=True),
            record.metadata_status,
            json.dumps(record.missing_required_fields, sort_keys=True),
            json.dumps(record.source_fields, sort_keys=True),
            json.dumps(record.raw_metadata, sort_keys=True),
            record.audio_md5,
            _serialize_profile(record.spectral_profile),
            _serialize_danceability_profile(record.danceability_profile),
            _serialize_edge_spectral_profile(record.edge_spectral_profile),
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
            energy_in=row["energy_in"],
            energy_out=row["energy_out"],
            energy_peak=row["energy_peak"],
            duration=row["duration"],
            genre=row["genre"],
            tags=json.loads(row["tags_json"]),
            metadata_status=row["metadata_status"],
            missing_required_fields=json.loads(row["missing_required_fields_json"]),
            source_fields=json.loads(row["source_fields_json"]),
            raw_metadata=json.loads(row["raw_metadata_json"]),
            audio_md5=row["audio_md5"],
            spectral_profile=_deserialize_profile(row["spectral_profile_json"]),
            danceability_profile=_deserialize_danceability_profile(row["danceability_profile_json"]),
            edge_spectral_profile=_deserialize_edge_spectral_profile(row["edge_spectral_profile_json"]),
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
            energy_in=row["energy_in"],
            energy_out=row["energy_out"],
            energy_peak=row["energy_peak"],
            duration=row["duration"],
            genre=row["genre"],
            tags=json.loads(row["tags_json"]),
            metadata_status=row["metadata_status"],
            missing_required_fields=json.loads(row["missing_required_fields_json"]),
            audio_md5=row["audio_md5"],
            spectral_profile=_deserialize_profile(row["spectral_profile_json"]),
            danceability_profile=_deserialize_danceability_profile(row["danceability_profile_json"]),
            edge_spectral_profile=_deserialize_edge_spectral_profile(row["edge_spectral_profile_json"]),
        )


def _serialize_profile(profile: SpectralProfile | None) -> str | None:
    if profile is None:
        return None
    return profile.model_dump_json()


def _deserialize_profile(value: str | None) -> SpectralProfile | None:
    if value is None:
        return None
    try:
        profile_data = json.loads(value)
        profile_data["dominant_color"] = dominant_color_for_ratios(
            profile_data["red_ratio"],
            profile_data["green_ratio"],
            profile_data["blue_ratio"],
        )
        return SpectralProfile.model_validate(profile_data)
    except Exception:
        return None


def _serialize_danceability_profile(profile: DanceabilityProfile | None) -> str | None:
    if profile is None:
        return None
    return profile.model_dump_json()


def _deserialize_danceability_profile(value: str | None) -> DanceabilityProfile | None:
    if value is None:
        return None
    try:
        return DanceabilityProfile.model_validate(json.loads(value))
    except Exception:
        return None


def _serialize_edge_spectral_profile(profile: EdgeSpectralProfile | None) -> str | None:
    if profile is None:
        return None
    return profile.model_dump_json()


def _deserialize_edge_spectral_profile(value: str | None) -> EdgeSpectralProfile | None:
    if value is None:
        return None
    try:
        return EdgeSpectralProfile.model_validate(json.loads(value))
    except Exception:
        return None
