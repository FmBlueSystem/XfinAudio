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

from xfinaudio.audio.analysis_planning import SpectralProfileCache, plan_analysis_paths, store_in_cache
from xfinaudio.audio.spectral_profile import SpectralProfile, analyze_spectral_profile

if TYPE_CHECKING:
    from xfinaudio.audio.analyzer import SpectralAnalyzer
    from xfinaudio.library.scan_service import ScanCancellationToken

LOGGER = logging.getLogger(__name__)


def _analyze_one(path_str: str) -> tuple[str, SpectralProfile | None]:
    """Worker entry point: must be importable by the process pool."""
    return path_str, analyze_spectral_profile(Path(path_str))


def _default_max_workers_for_analysis(cpu_count: int | None = None) -> int:
    """Return the default analysis pool size while reserving one CPU core."""
    return max(1, (cpu_count or os.cpu_count() or 4) - 1)


def analyze_paths(
    paths: list[Path],
    *,
    max_workers: int | None = None,
    executor: str = "thread",
    cache: SpectralProfileCache | None = None,
    on_progress: Callable[[Path], None] | None = None,
    cancellation_token: ScanCancellationToken | None = None,
    spectral_analyzer: SpectralAnalyzer | None = None,
) -> dict[str, SpectralProfile | None]:
    """Analyze a list of audio files, optionally in parallel with caching.

    Args:
        paths: Audio files to analyze. Order is not significant.
        max_workers: Upper bound for the executor pool. ``None`` picks a
            reasonable default that reserves one CPU core for the UI/OS.
        executor: ``"thread"`` uses ``ThreadPoolExecutor`` (low spawn overhead,
            good for librosa/numpy CPU-bound work). ``"process"`` uses
            ``ProcessPoolExecutor`` (higher overhead, sometimes better for very
            long files). ``"sequential"`` disables parallelism.
        cache: Optional mutable cache keyed by path string. Each entry stores
            ``(mtime_ns, size_bytes, profile)``. Cache hits skip analysis.
        on_progress: Called once for every path as its result becomes available.
        cancellation_token: Checked between results; pending work is cancelled
            and already-completed results are returned.
        spectral_analyzer: Optional analyzer boundary to use instead of the
            module-level librosa-backed analyzer.

    Returns:
        Mapping ``path_str -> SpectralProfile | None``. May be partial when
        cancellation was requested.
    """
    if max_workers is None:
        max_workers = _default_max_workers_for_analysis()

    plan = plan_analysis_paths(paths, cache=cache)
    results: dict[str, SpectralProfile | None] = dict(plan.results)
    paths_to_analyze = plan.pending_paths

    if on_progress is not None:
        for path in paths:
            if str(path) in plan.results:
                on_progress(path)

    if not paths_to_analyze:
        return results

    if len(paths_to_analyze) == 1 or max_workers < 2 or executor == "sequential":
        _run_sequential(paths_to_analyze, results, cache, on_progress, cancellation_token, spectral_analyzer)
        return results

    try:
        if spectral_analyzer is None:
            _run_parallel(
                paths_to_analyze,
                results,
                cache,
                max_workers,
                on_progress,
                cancellation_token,
                use_threads=executor == "thread",
            )
        else:
            _run_parallel_with_analyzer(
                paths_to_analyze,
                results,
                cache,
                max_workers,
                on_progress,
                cancellation_token,
                spectral_analyzer=spectral_analyzer,
                use_threads=executor == "thread",
            )
    except Exception as exc:  # pragma: no cover - defensive fallback
        LOGGER.warning("Parallel executor failed (%s); falling back to sequential analysis", exc)
        _run_sequential(paths_to_analyze, results, cache, on_progress, cancellation_token, spectral_analyzer)

    return results


def _run_sequential(
    paths: list[Path],
    results: dict[str, SpectralProfile | None],
    cache: SpectralProfileCache | None,
    on_progress: Callable[[Path], None] | None,
    cancellation_token: ScanCancellationToken | None,
    spectral_analyzer: SpectralAnalyzer | None = None,
) -> None:
    for path in paths:
        if cancellation_token is not None and cancellation_token.is_cancelled:
            break
        profile = spectral_analyzer.analyze(path) if spectral_analyzer is not None else analyze_spectral_profile(path)
        results[str(path)] = profile
        store_in_cache(path, profile, cache)
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
                store_in_cache(Path(path_str), profile, cache)
            except Exception:
                LOGGER.exception("Spectral analysis failed for %s", path)
                results[str(path)] = None
            if on_progress is not None:
                on_progress(path)


def _run_parallel_with_analyzer(
    paths: list[Path],
    results: dict[str, SpectralProfile | None],
    cache: SpectralProfileCache | None,
    max_workers: int,
    on_progress: Callable[[Path], None] | None,
    cancellation_token: ScanCancellationToken | None,
    *,
    spectral_analyzer: SpectralAnalyzer,
    use_threads: bool = True,
) -> None:
    pool_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
    with pool_class(max_workers=max_workers) as pool:
        future_to_path: dict[Future[SpectralProfile | None], Path] = {
            pool.submit(spectral_analyzer.analyze, path): path for path in paths
        }
        for future in as_completed(future_to_path):
            if cancellation_token is not None and cancellation_token.is_cancelled:
                for pending in future_to_path:
                    pending.cancel()
                break
            path = future_to_path[future]
            try:
                profile = future.result()
                results[str(path)] = profile
                store_in_cache(path, profile, cache)
            except Exception:
                LOGGER.exception("Spectral analysis failed for %s", path)
                results[str(path)] = None
            if on_progress is not None:
                on_progress(path)
