"""Batch spectral analysis with optional process-pool parallelism and caching.

The module is the "dispatch" layer for the Arbor-style optimization of Task 8:
it executes ``analyze_spectral_profile`` over many files while preserving
cancellation, progress reporting, and graceful fallback to sequential execution.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from xfinaudio.audio.spectral_profile import SpectralProfile, analyze_spectral_profile

if TYPE_CHECKING:
    from xfinaudio.library.scan_service import ScanCancellationToken

LOGGER = logging.getLogger(__name__)

SpectralProfileCache = dict[str, tuple[int, int, SpectralProfile]]


def _analyze_one(path_str: str) -> tuple[str, SpectralProfile | None]:
    """Worker entry point: must be importable by the process pool."""
    return path_str, analyze_spectral_profile(Path(path_str))


def _try_cached_profile(
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


def _store_in_cache(
    path: Path,
    profile: SpectralProfile | None,
    cache: SpectralProfileCache | None,
) -> None:
    if cache is None or profile is None:
        return
    try:
        stat = path.stat()
    except OSError:
        return
    cache[str(path)] = (stat.st_mtime_ns, stat.st_size, profile)


def analyze_paths(
    paths: list[Path],
    *,
    max_workers: int | None = None,
    executor: str = "thread",
    cache: SpectralProfileCache | None = None,
    on_progress: Callable[[Path], None] | None = None,
    cancellation_token: ScanCancellationToken | None = None,
) -> dict[str, SpectralProfile | None]:
    """Analyze a list of audio files, optionally in parallel with caching.

    Args:
        paths: Audio files to analyze. Order is not significant.
        max_workers: Upper bound for the executor pool. ``None`` picks a
            reasonable default based on CPU count (capped at 8).
        executor: ``"thread"`` uses ``ThreadPoolExecutor`` (low spawn overhead,
            good for librosa/numpy CPU-bound work). ``"process"`` uses
            ``ProcessPoolExecutor`` (higher overhead, sometimes better for very
            long files). ``"sequential"`` disables parallelism.
        cache: Optional mutable cache keyed by path string. Each entry stores
            ``(mtime_ns, size_bytes, profile)``. Cache hits skip analysis.
        on_progress: Called once for every path as its result becomes available.
        cancellation_token: Checked between results; pending work is cancelled
            and already-completed results are returned.

    Returns:
        Mapping ``path_str -> SpectralProfile | None``. May be partial when
        cancellation was requested.
    """
    if max_workers is None:
        max_workers = min(os.cpu_count() or 4, 8)

    results: dict[str, SpectralProfile | None] = {}
    paths_to_analyze: list[Path] = []

    for path in paths:
        cached_profile = _try_cached_profile(path, cache)
        if cached_profile is not None:
            results[str(path)] = cached_profile
            if on_progress is not None:
                on_progress(path)
            continue
        paths_to_analyze.append(path)

    if not paths_to_analyze:
        return results

    if len(paths_to_analyze) == 1 or max_workers < 2 or executor == "sequential":
        _run_sequential(paths_to_analyze, results, cache, on_progress, cancellation_token)
        return results

    try:
        _run_parallel(
            paths_to_analyze,
            results,
            cache,
            max_workers,
            on_progress,
            cancellation_token,
            use_threads=executor == "thread",
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        LOGGER.warning("Parallel executor failed (%s); falling back to sequential analysis", exc)
        _run_sequential(paths_to_analyze, results, cache, on_progress, cancellation_token)

    return results


def _run_sequential(
    paths: list[Path],
    results: dict[str, SpectralProfile | None],
    cache: SpectralProfileCache | None,
    on_progress: Callable[[Path], None] | None,
    cancellation_token: ScanCancellationToken | None,
) -> None:
    for path in paths:
        if cancellation_token is not None and cancellation_token.is_cancelled:
            break
        profile = analyze_spectral_profile(path)
        results[str(path)] = profile
        _store_in_cache(path, profile, cache)
        if on_progress is not None:
            on_progress(path)


def _run_parallel(
    paths: list[Path],
    results: dict[str, SpectralProfile | None],
    cache: SpectralProfileCache | None,
    max_workers: int,
    on_progress: Callable[[Path], None] | None,
    cancellation_token: ScanCancellationToken | None,
    use_threads: bool = True,
) -> None:
    pool_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
    with pool_class(max_workers=max_workers) as pool:
        future_to_path: dict[Future[tuple[str, SpectralProfile | None]], Path] = {
            pool.submit(_analyze_one, str(path)): path for path in paths
        }
        for future in as_completed(future_to_path):
            if cancellation_token is not None and cancellation_token.is_cancelled:
                for pending in future_to_path:
                    pending.cancel()
                break
            path = future_to_path[future]
            try:
                path_str, profile = future.result()
                results[path_str] = profile
                _store_in_cache(Path(path_str), profile, cache)
            except Exception:
                LOGGER.exception("Spectral analysis failed for %s", path)
                results[str(path)] = None
            if on_progress is not None:
                on_progress(path)
