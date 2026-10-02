"""Filesystem identity bindings for explicitly granted Serato folders only."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from xfinaudio.exporting.serato_crate import MAX_ANCHORED_CRATE_BYTES
from xfinaudio.headless.common import BackendError

DirectoryIdentity = tuple[int, int]
FileIdentity = tuple[int, int, int, int]


def opaque_id(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise BackendError("invalid_params", "Invalid export identity") from error
    return value


def crate_name(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or value in {".", ".."}
        or any(char in value for char in "/\\:")
        or any(unicodedata.category(char).startswith("C") for char in value)
    ):
        raise BackendError("invalid_params", "Choose a simple crate name without separators or control characters")
    try:
        if len((value + ".crate").encode("utf-8")) > 240:
            raise ValueError
    except (ValueError, UnicodeError) as error:
        raise BackendError("invalid_params", "Crate name is too long") from error
    return value


@contextmanager
def open_directory(path: Path) -> Iterator[tuple[int, tuple[DirectoryIdentity, ...]]]:
    """Open each absolute path component without symlinks and retain the leaf fd."""
    if not path.is_absolute() or ".." in path.parts:
        raise OSError("Absolute confined directory required")
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        lineage = [(info.st_dev, info.st_ino)]
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            info = os.fstat(descriptor)
            lineage.append((info.st_dev, info.st_ino))
        yield descriptor, tuple(lineage)
    finally:
        os.close(descriptor)


def directory_identity(path: Path) -> tuple[DirectoryIdentity, ...]:
    with open_directory(path) as (_, lineage):
        return lineage


def file_identity(path: Path) -> FileIdentity | None:
    with open_directory(path.parent) as (descriptor, _):
        try:
            info = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(info.st_mode):
            raise OSError("Expected a regular file")
        return info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size


def source_identity(path: Path) -> tuple[object, ...]:
    with open_directory(path.parent) as (descriptor, lineage):
        info = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise OSError("Expected a regular source file")
        return lineage, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def target_state(path: Path) -> tuple[FileIdentity | None, str | None]:
    """Bind existing bytes too, so a changed file cannot impersonate the preview."""
    identity = file_identity(path)
    if identity is None:
        return None, None
    if identity[3] > MAX_ANCHORED_CRATE_BYTES:
        raise OSError("Crate exceeds the supported byte limit")
    with open_directory(path.parent) as (directory_fd, _):
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        with os.fdopen(descriptor, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise OSError("Expected a regular crate")
            content = handle.read(MAX_ANCHORED_CRATE_BYTES + 1)
            if len(content) > MAX_ANCHORED_CRATE_BYTES:
                raise OSError("Crate exceeds the supported byte limit")
            digest = hashlib.sha256(content).hexdigest()
    if file_identity(path) != identity:
        raise OSError("Crate changed while previewing")
    return identity, digest


def backup_target(target: Path) -> Path:
    base = target.with_name(target.name + ".bak")
    for index in range(1000):
        candidate = base if not index else base.with_name(f"{base.name}.{index}")
        if file_identity(candidate) is None:
            return candidate
    raise OSError("Too many backup collisions")


def volume_root(path: Path) -> Path:
    """Use mounted source-volume identity, never the selected Serato folder's parent."""
    if path.parts[:2] == ("/", "Volumes") and len(path.parts) >= 3:
        return Path(*path.parts[:3])
    if sys.platform == "darwin":
        # APFS firmlinks can change st_dev at /Users without introducing a
        # Serato drive root. Internal references still begin with Users/....
        return Path("/")
    current = path if path.is_dir() else path.parent
    device = current.stat().st_dev
    while current.parent != current and current.parent.stat().st_dev == device:
        current = current.parent
    return current
