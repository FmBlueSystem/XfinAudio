"""Pure planning helpers for batch spectral analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from xfinaudio.audio.spectral_profile import SpectralProfile
else:
    SpectralProfile = Any

SpectralProfileCache: TypeAlias = dict[str, tuple[int, int, SpectralProfile]]


@dataclass(frozen=True)
class AnalysisPlan:
    """Immediate cache results and unique paths still requiring analysis."""

    results: dict[str, SpectralProfile]
    pending_paths: list[Path]


def plan_analysis_paths(
    paths: list[Path],
    *,
    cache: SpectralProfileCache | None,
) -> AnalysisPlan:
    """Return cached results and unique uncached paths for analysis."""
    results: dict[str, SpectralProfile] = {}
    pending_paths: list[Path] = []
    seen_pending: set[str] = set()

    for path in paths:
        path_str = str(path)
        cached_profile = try_cached_profile(path, cache)
        if cached_profile is not None:
            results[path_str] = cached_profile
            continue
        if path_str in seen_pending:
            continue
        seen_pending.add(path_str)
        pending_paths.append(path)

    return AnalysisPlan(results=results, pending_paths=pending_paths)


def try_cached_profile(
    path: Path,
    cache: SpectralProfileCache | None,
) -> SpectralProfile | None:
    """Return the cached profile for *path* if mtime and size still match."""
    if cache is None:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    cached = cache.get(str(path))
    if cached is None:
        return None
    if cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
        return cached[2]
    return None


def store_in_cache(
    path: Path,
    profile: SpectralProfile | None,
    cache: SpectralProfileCache | None,
) -> None:
    """Store a non-empty profile in the cache using current file metadata."""
    if cache is None or profile is None:
        return
    try:
        stat = path.stat()
    except OSError:
        return
    cache[str(path)] = (stat.st_mtime_ns, stat.st_size, profile)


__all__ = ["AnalysisPlan", "SpectralProfileCache", "plan_analysis_paths", "store_in_cache", "try_cached_profile"]
