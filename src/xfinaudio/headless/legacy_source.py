"""Read selected legacy app files without SQLite/source/audio side effects."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_safety import open_directory

MAX_DATABASE_BYTES = 256 * 1024 * 1024
MAX_SETTINGS_BYTES = 256 * 1024
SOURCE_FILES = ("xfinaudio.sqlite3", "playlists.db", "settings.json")
DESTINATION_FILES = ("tracks.db", "playlists.db", "settings.json")


def invalid() -> BackendError:
    return BackendError("legacy_invalid", "Selected legacy files are unsupported, unsafe, or too large")


def directory(value: Any) -> Path:
    if not isinstance(value, (str, Path)) or not str(value) or len(str(value)) > 4096 or "\x00" in str(value):
        raise invalid()
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or str(path) != str(value):
        raise invalid()
    for part in reversed((path, *path.parents)):
        if not stat.S_ISDIR(part.lstat().st_mode):
            raise invalid()
    return path


def read_file(path: Path, limit: int, directory_fd: int | None = None) -> bytes | None:
    if directory_fd is None:
        with open_directory(path.parent) as (descriptor, _):
            return read_file(path, limit, descriptor)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise invalid()
        content = handle.read(limit + 1)
        after = os.fstat(handle.fileno())

        def identity(info):
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

        final = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        if len(content) > limit or identity(before) != identity(after) or identity(after) != identity(final):
            raise invalid()
        return content


def signature(content: bytes | None) -> str:
    return hashlib.sha256(b"\0" if content is None else b"\1" + content).hexdigest()


def no_sidecars(root: Path, names: tuple[str, ...], directory_fd: int | None = None) -> None:
    if directory_fd is None:
        with open_directory(root) as (descriptor, _):
            return no_sidecars(root, names, descriptor)
    for name in names:
        for suffix in ("-wal", "-shm", "-journal"):
            try:
                os.stat(name + suffix, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise BackendError("legacy_source_active", "Close and checkpoint the old app before importing")


def snapshot(root: Path, names: tuple[str, ...] = SOURCE_FILES) -> dict[str, bytes | None]:
    directory(root)
    with open_directory(root) as (descriptor, lineage):
        no_sidecars(root, names, descriptor)
        content = {
            name: read_file(
                root / name, MAX_SETTINGS_BYTES if name.endswith(".json") else MAX_DATABASE_BYTES, descriptor
            )
            for name in names
        }
        no_sidecars(root, names, descriptor)
        for name, original in content.items():
            if (
                read_file(root / name, MAX_SETTINGS_BYTES if name.endswith(".json") else MAX_DATABASE_BYTES, descriptor)
                != original
            ):
                raise BackendError("stale_legacy", "Selected files changed; close the old app and preview again")
        no_sidecars(root, names, descriptor)
        with open_directory(root) as (_, current_lineage):
            if current_lineage != lineage:
                raise invalid()
        return content


def safe_preferences(content: bytes | None) -> tuple[bytes, dict[str, float]]:
    from xfinaudio.config.settings import AppSettings, AudioSettings, ScoringSettings

    payload = {} if content is None else json.loads(content)
    if not isinstance(payload, dict) or payload.get("settings_version", 1) != 1:
        raise invalid()
    audio, scoring = payload.get("audio", {}), payload.get("scoring", {})
    if not isinstance(audio, dict) or not isinstance(scoring, dict):
        raise invalid()
    volume, cohesion = audio.get("preview_volume", 0.7), scoring.get("spectral_cohesion", 0.5)
    if any(type(value) not in (int, float) or not 0 <= value <= 1 for value in (volume, cohesion)):
        raise invalid()
    defaults = AppSettings()
    settings = defaults.model_copy(
        update={
            "audio": AudioSettings(preview_volume=volume),
            "scoring": ScoringSettings(spectral_cohesion=cohesion),
            "library": defaults.library.model_copy(update={"watch_for_changes": False}),
            "loudness": defaults.loudness.model_copy(update={"enabled": False}),
        }
    )
    return settings.model_dump_json().encode(), {"previewVolume": float(volume), "spectralCohesion": float(cohesion)}
