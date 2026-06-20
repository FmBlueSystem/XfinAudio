"""Pure scan candidate planning for library scans."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"})

PathLister = Callable[[Path], Iterable[Path]]


def plan_supported_audio_paths(folder: Path, *, list_paths: PathLister) -> list[Path]:
    """Return unique supported audio paths in deterministic order."""
    planned: list[Path] = []
    seen: set[str] = set()
    for path in sorted(list_paths(folder), key=lambda candidate: str(candidate)):
        if not is_supported_audio_file(path):
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        planned.append(path)
    return planned


def is_supported_audio_file(path: Path) -> bool:
    """Return whether a path has a supported audio extension."""
    return path.suffix.casefold() in SUPPORTED_AUDIO_EXTENSIONS


__all__ = ["SUPPORTED_AUDIO_EXTENSIONS", "PathLister", "is_supported_audio_file", "plan_supported_audio_paths"]
