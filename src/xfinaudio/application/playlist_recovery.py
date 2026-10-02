"""Atomic app-owned saved-set recovery; never opens or modifies referenced audio."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from xfinaudio.library.playlist_models import Playlist
from xfinaudio.library.sqlite_connection import database_connection


class PlaylistRecovery:
    """Retain exact snapshots until explicitly restored, with no permanent-delete API."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        with database_connection(db_path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS deleted_playlists ("
                "deletion_id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, deleted_at TEXT NOT NULL, "
                "restored_id INTEGER)"
            )

    @staticmethod
    def _snapshot(playlist: Playlist) -> str:
        return json.dumps(asdict(playlist), default=lambda value: value.isoformat(), ensure_ascii=False)

    def archive(self, original: Playlist) -> str | None:
        with database_connection(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM playlists WHERE id = ?", (original.id,)).fetchone()
            paths = [
                r["track_path"]
                for r in db.execute(
                    "SELECT track_path FROM playlist_tracks WHERE playlist_id = ? ORDER BY position", (original.id,)
                )
            ]
            if (
                row is None
                or row["name"] != original.name
                or paths != original.track_paths
                or (
                    datetime.fromisoformat(row["created_at"]) != original.created_at
                    or datetime.fromisoformat(row["updated_at"]) != original.updated_at
                )
            ):
                return None
            identity = str(uuid4())
            db.execute(
                "INSERT INTO deleted_playlists (deletion_id,snapshot,deleted_at) VALUES (?,?,?)",
                (identity, self._snapshot(original), datetime.now(UTC).isoformat()),
            )
            db.execute("DELETE FROM playlists WHERE id = ?", (original.id,))
            return identity

    def list_deleted(self) -> list[dict[str, Any]]:
        with database_connection(self.db_path) as db:
            rows = db.execute(
                "SELECT * FROM deleted_playlists WHERE restored_id IS NULL ORDER BY deleted_at DESC"
            ).fetchall()
        return [
            {
                "deletionId": row["deletion_id"],
                "name": (snapshot := json.loads(row["snapshot"]))["name"],
                "trackCount": len(snapshot["track_paths"]),
                "deletedAt": row["deleted_at"],
            }
            for row in rows
        ]

    def restore(self, identity: str) -> int | None:
        with database_connection(self.db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT snapshot FROM deleted_playlists WHERE deletion_id = ? AND restored_id IS NULL", (identity,)
            ).fetchone()
            if row is None:
                return None
            snapshot = json.loads(row["snapshot"])
            cursor = db.execute(
                "INSERT INTO playlists (name,created_at,updated_at) VALUES (?,?,?)",
                (snapshot["name"], snapshot["created_at"], datetime.now().isoformat()),
            )
            new_id = cursor.lastrowid
            assert new_id is not None
            db.executemany(
                "INSERT INTO playlist_tracks (playlist_id,track_path,position) VALUES (?,?,?)",
                [(new_id, path, index) for index, path in enumerate(snapshot["track_paths"])],
            )
            db.execute("UPDATE deleted_playlists SET restored_id = ? WHERE deletion_id = ?", (new_id, identity))
            return new_id
