"""Fresh-profile-only import with retained backups and fail-closed crash recovery."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from xfinaudio.headless.common import BackendError
from xfinaudio.headless.legacy_source import (
    DESTINATION_FILES,
    MAX_DATABASE_BYTES,
    directory,
    invalid,
    no_sidecars,
    read_file,
    safe_preferences,
    signature,
    snapshot,
)
from xfinaudio.headless.legacy_validation import memory_database, rebuild_playlists, rebuild_tracks
from xfinaudio.headless.serato_safety import open_directory

LEGACY_FIELDS = {
    "legacy.preview": {"source"},
    "legacy.apply": {"previewId", "confirmed"},
    "legacy.discard": {"previewId"},
}
JOURNAL = ".legacy-import-journal.json"
TOKEN = re.compile(r"^[0-9a-f]{32}$")


def durable_write(path: Path, content: bytes) -> None:
    with open_directory(path.parent) as (parent, _):
        descriptor = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())


def move(source: Path, target: Path) -> None:
    with open_directory(source.parent) as (source_fd, _), open_directory(target.parent) as (target_fd, _):
        os.replace(source.name, target.name, src_dir_fd=source_fd, dst_dir_fd=target_fd)


def publish(source: Path, target: Path) -> None:
    # Link is atomic and refuses an independently created destination, unlike rename.
    with open_directory(source.parent) as (source_fd, _), open_directory(target.parent) as (target_fd, _):
        os.link(source.name, target.name, src_dir_fd=source_fd, dst_dir_fd=target_fd, follow_symlinks=False)
        os.unlink(source.name, dir_fd=source_fd)  # Only our disposable publish temp, never a backup.


def make_directory(path: Path) -> None:
    with open_directory(path.parent) as (parent, _):
        os.mkdir(path.name, mode=0o700, dir_fd=parent)


def sync_directory(path: Path) -> None:
    with open_directory(path) as (descriptor, _):
        os.fsync(descriptor)


def write_journal(root: Path, record: dict[str, Any]) -> None:
    content = json.dumps(record, sort_keys=True).encode()
    workspace = directory(root / (".legacy-import-" + record["id"]))
    durable_write(workspace / ("journal-" + uuid4().hex + ".json"), content)
    temporary = root / (".legacy-journal-" + uuid4().hex)
    durable_write(temporary, content)
    move(temporary, root / JOURNAL)
    sync_directory(root)


def recover_legacy_import(data_dir: Path | str) -> bool:
    """Must run before opening any destination repository. Never trust stored paths."""
    root = directory(data_dir)
    try:
        content = read_file(root / JOURNAL, 16384)
        if content is None:
            return False
        record = json.loads(content)
        if (
            not isinstance(record, dict)
            or set(record) != {"id", "phase", "before", "after"}
            or not isinstance(record["id"], str)
            or not TOKEN.fullmatch(record["id"])
        ):
            raise invalid()
        if record["phase"] not in ("prepared", "committed", "rolled_back"):
            raise invalid()
        for section in ("before", "after"):
            if not isinstance(record[section], dict) or set(record[section]) != set(DESTINATION_FILES):
                raise invalid()
            if any(
                value is not None and (not isinstance(value, str) or re.fullmatch("[a-f0-9]{64}", value) is None)
                for value in record[section].values()
            ):
                raise invalid()
        if record["phase"] != "prepared":
            return record["phase"] == "committed"
        workspace = directory(root / (".legacy-import-" + record["id"]))
        backup = directory(workspace / "backup")
        no_sidecars(root, DESTINATION_FILES)
        originals = {}
        for name in DESTINATION_FILES:
            originals[name] = read_file(backup / name, MAX_DATABASE_BYTES)
            expected = record["before"][name]
            outgoing = read_file(workspace / ("outgoing-" + name), MAX_DATABASE_BYTES)
            if outgoing is not None and signature(outgoing) != expected:
                raise invalid()
            if (None if originals[name] is None else signature(originals[name])) != expected:
                raise invalid()
        # Unexpected concurrent data blocks rollback, rather than overwriting newer work.
        current_files = snapshot(root, DESTINATION_FILES)
        for name, current in current_files.items():
            digest = None if current is None else signature(current)
            if digest not in (None, record["before"][name], record["after"][name]):
                raise invalid()
        # All backups and current bytes validate before any restoration.
        for name in DESTINATION_FILES:
            current = read_file(root / name, MAX_DATABASE_BYTES)
            if current is not None:
                move(root / name, workspace / ("interrupted-" + uuid4().hex + "-" + name))
            if originals[name] is not None:
                durable_write(root / name, originals[name])
        sync_directory(root)
        record["phase"] = "rolled_back"
        write_journal(root, record)
        return False
    except (OSError, ValueError, TypeError, BackendError) as error:
        raise BackendError(
            "legacy_recovery_required", "Import recovery needs attention; retained backups were not deleted"
        ) from error


class LegacyImport:
    def __init__(self, backend: Any) -> None:
        self.backend = backend
        self.pending: dict[str, Any] | None = None
        self.restart_required = False

    def _fresh(self) -> dict[str, bytes | None]:
        root = directory(self.backend.data_dir)
        files = snapshot(root, DESTINATION_FILES)
        if self.backend.roots:
            raise BackendError("legacy_destination_not_empty", "Import requires a fresh profile without root grants")
        for filename, table in (("tracks.db", "tracks"), ("playlists.db", "playlists")):
            content = files[filename]
            if content is not None:
                with memory_database(content) as database:
                    if database.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
                        raise BackendError(
                            "legacy_destination_not_empty",
                            "Import requires a fresh profile without tracks or saved sets",
                        )
        roots = read_file(root / "roots.json", 262144)
        if roots not in (None, b"[]") or files["settings.json"] is not None:
            raise BackendError(
                "legacy_destination_not_empty", "Import requires a fresh profile without settings or root grants"
            )
        return files

    def execute(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in LEGACY_FIELDS or not isinstance(params, dict) or set(params) != LEGACY_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected legacy import fields")
        if self.restart_required:
            raise BackendError("legacy_restart_required", "Restart before using imported data")
        try:
            if method == "legacy.preview":
                self.pending = None
                return self._preview(params["source"])
            token = params["previewId"]
            if (
                not isinstance(token, str)
                or not TOKEN.fullmatch(token)
                or self.pending is None
                or token != self.pending["id"]
            ):
                raise BackendError("stale_legacy", "Preview the selected legacy data again")
            if method == "legacy.discard":
                self.pending = None
                return {"discarded": True}
            if params["confirmed"] is not True:
                raise BackendError("confirmation_required", "Native confirmation is required")
            return self._apply()
        except (OSError, ValueError, TypeError, sqlite3.Error) as error:
            self.pending = None
            raise invalid() from error

    def _preview(self, selected: Any) -> dict[str, Any]:
        source = directory(selected)
        root = directory(self.backend.data_dir)
        if source == root or source.is_relative_to(root) or root.is_relative_to(source):
            raise invalid()
        before = self._fresh()
        content = snapshot(source)
        if content["xfinaudio.sqlite3"] is None and content["playlists.db"] is None:
            raise invalid()
        if len(list(root.glob(".legacy-import-*"))) >= 20:
            raise BackendError("legacy_storage_full", "Review retained import backups before creating another preview")
        token = uuid4().hex
        workspace = root / (".legacy-import-" + token)
        make_directory(workspace)
        ready = workspace / "ready"
        make_directory(ready)
        tracks, track_count, cache_count = rebuild_tracks(content["xfinaudio.sqlite3"])
        durable_write(ready / "tracks.db", tracks)
        playlists, playlist_count, references, names = rebuild_playlists(content["playlists.db"])
        durable_write(ready / "playlists.db", playlists)
        settings, safe = safe_preferences(content["settings.json"])
        durable_write(ready / "settings.json", settings)
        staged = snapshot(ready, DESTINATION_FILES)
        public = {
            "previewId": token,
            "mode": "fresh-profile-only",
            "trackCount": track_count,
            "cachedTrackCount": cache_count,
            "playlistCount": playlist_count,
            "referenceCount": references,
            "playlistNames": names,
            "safePreferences": safe,
            "requiresRootAuthorization": True,
            "sourceUnchanged": True,
        }
        self.pending = {
            "id": token,
            "source": source,
            "sourceSignatures": {key: signature(value) for key, value in content.items()},
            "before": before,
            "staged": {key: signature(value) for key, value in staged.items()},
            "public": public,
        }
        return public

    def _apply(self) -> dict[str, Any]:
        assert self.pending is not None
        pending, self.pending = self.pending, None
        root = directory(self.backend.data_dir)
        try:
            before = self._fresh()
            current = snapshot(pending["source"])
            if (
                before != pending["before"]
                or {key: signature(value) for key, value in current.items()} != pending["sourceSignatures"]
            ):
                raise invalid()
        except (OSError, ValueError, BackendError) as error:
            raise BackendError("stale_legacy", "Source or destination changed; preview again") from error
        workspace = directory(root / (".legacy-import-" + pending["id"]))
        ready = directory(workspace / "ready")
        staged = snapshot(ready, DESTINATION_FILES)
        if {key: signature(value) for key, value in staged.items()} != pending["staged"]:
            raise BackendError("stale_legacy", "Prepared import changed; preview again")
        backup = workspace / "backup"
        make_directory(backup)
        for name, content in before.items():
            if content is not None:
                durable_write(backup / name, content)
        sync_directory(backup)
        sync_directory(workspace)
        record = {
            "id": pending["id"],
            "phase": "prepared",
            "before": {key: None if value is None else signature(value) for key, value in before.items()},
            "after": pending["staged"],
        }
        self.restart_required = True
        try:
            write_journal(root, record)
            expected = dict(before)
            if (
                self._fresh() != before
                or {key: signature(value) for key, value in snapshot(pending["source"]).items()}
                != pending["sourceSignatures"]
            ):
                raise invalid()
            for name, content in staged.items():
                assert content is not None
                temporary = workspace / ("commit-" + name)
                durable_write(temporary, content)
                if snapshot(root, DESTINATION_FILES) != expected or read_file(root / "roots.json", 262144) not in (
                    None,
                    b"[]",
                ):
                    raise invalid()
                if before[name] is not None:
                    outgoing = workspace / ("outgoing-" + name)
                    move(root / name, outgoing)
                    if read_file(outgoing, MAX_DATABASE_BYTES) != before[name]:
                        raise invalid()
                publish(temporary, root / name)
                expected[name] = content
            if (
                snapshot(root, DESTINATION_FILES) != expected
                or read_file(root / "roots.json", 262144) not in (None, b"[]")
                or {key: signature(value) for key, value in snapshot(pending["source"]).items()}
                != pending["sourceSignatures"]
            ):
                raise invalid()
            sync_directory(root)
            record["phase"] = "committed"
            write_journal(root, record)
        except (OSError, BackendError) as error:
            if recover_legacy_import(root):
                raise BackendError(
                    "legacy_restart_required", "Import committed; restart before inspecting the profile"
                ) from error
            self.restart_required = False
            raise BackendError(
                "legacy_import_failed", "Import failed; the previous profile was restored and backups retained"
            ) from error
        return {
            "imported": True,
            "restartRequired": True,
            "backupRetained": True,
            "requiresRootAuthorization": True,
            "trackCount": pending["public"]["trackCount"],
            "playlistCount": pending["public"]["playlistCount"],
        }
