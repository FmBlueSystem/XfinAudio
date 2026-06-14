"""SQLite persistence for playlists."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from xfinaudio.library.playlist_models import Playlist, PlaylistSummary


class PlaylistRepository:
    """Persist playlists and their ordered track references."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._initialize()

    def create(self, name: str, track_paths: list[str]) -> Playlist:
        """Create a new playlist with ordered tracks."""
        now = datetime.now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO playlists (name, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (name, now.isoformat(), now.isoformat()),
            )
            playlist_id = cursor.lastrowid
            assert playlist_id is not None
            self._insert_tracks(connection, playlist_id, track_paths)
        return self.get_by_id(playlist_id)  # type: ignore[return-value]

    def list_summaries(self) -> list[PlaylistSummary]:
        """Return lightweight summaries of all playlists."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    COUNT(pt.track_path) AS track_count,
                    p.updated_at
                FROM playlists p
                LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
            ).fetchall()
        return [
            PlaylistSummary(
                id=row["id"],
                name=row["name"],
                track_count=row["track_count"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def get_by_id(self, playlist_id: int) -> Playlist | None:
        """Fetch a full playlist by id, or None if not found."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, created_at, updated_at FROM playlists WHERE id = ?",
                (playlist_id,),
            ).fetchone()
            if row is None:
                return None
            track_rows = connection.execute(
                "SELECT track_path FROM playlist_tracks WHERE playlist_id = ? ORDER BY position",
                (playlist_id,),
            ).fetchall()
        return Playlist(
            id=row["id"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            track_paths=[r["track_path"] for r in track_rows],
        )

    def update_name(self, playlist_id: int, name: str) -> None:
        """Rename a playlist."""
        now = datetime.now().isoformat()
        with self._connect() as connection:
            connection.execute(
                "UPDATE playlists SET name = ?, updated_at = ? WHERE id = ?",
                (name, now, playlist_id),
            )

    def update_tracks(self, playlist_id: int, track_paths: list[str]) -> None:
        """Replace all tracks in a playlist."""
        now = datetime.now().isoformat()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM playlist_tracks WHERE playlist_id = ?",
                (playlist_id,),
            )
            self._insert_tracks(connection, playlist_id, track_paths)
            connection.execute(
                "UPDATE playlists SET updated_at = ? WHERE id = ?",
                (now, playlist_id),
            )

    def duplicate(self, playlist_id: int) -> Playlist:
        """Duplicate a playlist with '(copy)' suffix."""
        original = self.get_by_id(playlist_id)
        if original is None:
            raise ValueError(f"Playlist {playlist_id} not found")
        return self.create(f"{original.name} (copy)", list(original.track_paths))

    def delete(self, playlist_id: int) -> None:
        """Delete a playlist and its tracks."""
        with self._connect() as connection:
            connection.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._ensure_schema(connection)

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id INTEGER NOT NULL,
                track_path TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (playlist_id, position),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON playlist_tracks(playlist_id)")

    @staticmethod
    def _insert_tracks(
        connection: sqlite3.Connection,
        playlist_id: int,
        track_paths: list[str],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO playlist_tracks (playlist_id, track_path, position)
            VALUES (?, ?, ?)
            """,
            [(playlist_id, path, idx) for idx, path in enumerate(track_paths)],
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
