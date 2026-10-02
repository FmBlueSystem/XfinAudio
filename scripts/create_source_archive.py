#!/usr/bin/env python3
"""Build a reproducible source handoff without generated trees or symlink traversal."""

from __future__ import annotations

import argparse
import gzip
import os
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

_EXCLUDED = {
    ".git",
    ".venv",
    ".venv-headless",
    "node_modules",
    ".out",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pyright",
    "build",
    "dist",
    ".release-evidence",
    ".worktrees",
    "release-dist",
    "htmlcov",
    ".DS_Store",
}


def source_files(root: Path) -> list[tuple[str, Path, os.stat_result]]:
    """List tracked and non-ignored source; reject unexpected link/special entries."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
    )
    selected: list[tuple[str, Path, os.stat_result]] = []
    for raw in sorted(set(result.stdout.split(b"\0")) - {b""}):
        name = raw.decode("utf-8", errors="strict")
        relative = PurePosixPath(name)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError("Unsafe source member")
        if any(part in _EXCLUDED or part.startswith(".coverage") for part in relative.parts):
            continue
        if any(part in {".env", ".aws", ".ssh"} or part.endswith(".env") for part in relative.parts):
            raise ValueError("Sensitive configuration cannot enter source archive")
        current = root
        for part in relative.parts:
            current /= part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError(f"Unexpected source symlink: {name}")
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"Non-regular source member: {name}")
        selected.append((name, current, info))
    return selected


def _identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def create_archive(root: Path, output: Path) -> int:
    root = root.resolve(strict=True)
    output = output.absolute()
    parent = output.parent.resolve(strict=True)
    if parent == root or parent.is_relative_to(root):
        raise ValueError("Source archive must be outside the source checkout")
    files = source_files(root)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=parent, prefix=".source-", suffix=".tmp", delete=False) as raw:
            temporary = Path(raw.name)
            with (
                gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
                tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive,
            ):
                for name, filename, before in files:
                    # Recheck all ancestors before opening, then use no-follow and identity.
                    if filename.resolve(strict=True) != filename:
                        raise ValueError("Source path changed during archiving")
                    descriptor = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW)
                    with os.fdopen(descriptor, "rb") as stream:
                        current = os.fstat(stream.fileno())
                        if not stat.S_ISREG(current.st_mode) or _identity(current) != _identity(before):
                            raise ValueError("Source file changed during archiving")
                        member = tarfile.TarInfo(name)
                        member.size = current.st_size
                        member.mode = 0o755 if current.st_mode & 0o111 else 0o644
                        member.mtime = 0
                        archive.addfile(member, stream)
                        if _identity(os.fstat(stream.fileno())) != _identity(before):
                            raise ValueError("Source file changed during archiving")
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, parent / output.name)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(f"Archived {create_archive(args.root, args.output)} regular source files")


if __name__ == "__main__":
    main()
