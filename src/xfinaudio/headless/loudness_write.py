"""Bind original loudness tag writing to confirmed file descriptors and retain backups."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from contextlib import ExitStack, suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

from mutagen import File as MutagenFile

from xfinaudio.audio.loudness import LoudnessProfile
from xfinaudio.audio.loudness_tags import LoudnessTagWriteResult, LoudnessTagWriteStatus, write_loudness_tags
from xfinaudio.exporting.serato_crate import _publish_exclusive
from xfinaudio.headless.serato_safety import open_directory, source_identity

SourceBinding = tuple[object, ...]


def bind_source(path: Path) -> SourceBinding:
    """Bind canonical parent lineage and current regular-file identity, without reading audio."""
    return source_identity(path)


def _identity(info: os.stat_result, lineage: object) -> SourceBinding:
    if not stat.S_ISREG(info.st_mode):
        raise OSError("Loudness requires a regular confirmed file")
    return lineage, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


class BoundLoudnessWriter:
    """Use the original format writer; its load/save hooks cannot reopen an arbitrary path."""

    def __init__(self, data_dir: Path, bindings: dict[str, SourceBinding]) -> None:
        self.data_dir = data_dir
        self.bindings = dict(bindings)
        self.run_id = str(uuid4())
        self.backups: list[Path] = []
        self.changed_count = 0
        self.unchanged_count = 0
        self.failed_count = 0

    def ensure_current(self, path: Path) -> None:
        if str(path) not in self.bindings or bind_source(path) != self.bindings[str(path)]:
            raise OSError("Confirmed loudness source changed")

    def _backup(self, path: Path, handle: Any, guard: Any) -> None:
        """Stream and fsync an exclusive app-owned backup before Mutagen may save."""
        leaf = hashlib.sha256(str(path).encode()).hexdigest() + ".bak"
        with open_directory(self.data_dir) as (data_fd, _):
            with suppress(FileExistsError):
                os.mkdir("loudness-backups", mode=0o700, dir_fd=data_fd)
            backup_fd = os.open("loudness-backups", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=data_fd)
            try:
                with suppress(FileExistsError):
                    os.mkdir(self.run_id, mode=0o700, dir_fd=backup_fd)
                run_fd = os.open(self.run_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=backup_fd)
                try:
                    descriptor = os.open(
                        leaf + ".pending", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=run_fd
                    )
                    with os.fdopen(descriptor, "wb") as target:
                        guard()
                        handle.seek(0)
                        digest = hashlib.sha256()
                        length = 0
                        while chunk := handle.read(1024 * 1024):
                            target.write(chunk)
                            digest.update(chunk)
                            length += len(chunk)
                        target.flush()
                        os.fsync(target.fileno())
                        guard()
                    _publish_exclusive(leaf + ".pending", leaf, run_fd)
                    os.fsync(run_fd)
                    self.backups.append(self.data_dir / "loudness-backups" / self.run_id / leaf)
                    manifest = {
                        "schema": 1,
                        "originalPath": str(path),
                        "originalBytes": length,
                        "sha256": digest.hexdigest(),
                        "backupFile": leaf,
                    }
                    manifest_fd = os.open(
                        leaf + ".json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=run_fd
                    )
                    with os.fdopen(manifest_fd, "w", encoding="utf-8") as output:
                        json.dump(manifest, output, ensure_ascii=False)
                        output.flush()
                        os.fsync(output.fileno())
                    os.fsync(run_fd)
                finally:
                    os.close(run_fd)
            finally:
                os.close(backup_fd)

    def __call__(self, path: Path, profile: LoudnessProfile) -> LoudnessTagWriteResult:
        try:
            with ExitStack() as stack:
                handle: Any = None
                lineage: object = None

                def guard() -> None:
                    self.ensure_current(path)
                    if handle is None or _identity(os.fstat(handle.fileno()), lineage) != self.bindings[str(path)]:
                        raise OSError("Confirmed loudness descriptor changed")

                def load_audio(_path: Path) -> Any:
                    nonlocal handle, lineage
                    self.ensure_current(path)
                    parent_fd, lineage = stack.enter_context(open_directory(path.parent))
                    descriptor = os.open(path.name, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
                    handle = stack.enter_context(os.fdopen(descriptor, "r+b"))
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    guard()
                    handle.seek(0)
                    return MutagenFile(fileobj=handle)

                def save_audio(audio: Any) -> None:
                    guard()
                    self._backup(path, handle, guard)
                    guard()
                    handle.seek(0)
                    audio.save(fileobj=handle)
                    handle.flush()
                    os.fsync(handle.fileno())

                result = write_loudness_tags(path, profile, load_audio=load_audio, save_audio=save_audio)
                if result.status is LoudnessTagWriteStatus.CHANGED:
                    self.changed_count += 1
                elif result.status is LoudnessTagWriteStatus.UNCHANGED:
                    self.unchanged_count += 1
                return result
        except Exception:
            self.failed_count += 1
            raise
