"""Benchmark harness for spectral-analysis optimizations.

Runs sequential, parallel, cached, and combined configurations over a directory
of audio files and writes a JSON/Markdown report. This is the dev evaluator for
the Arbor-style optimization of Task 8.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import tempfile
import time
import wave
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from xfinaudio.audio.batch_analyzer import analyze_paths
from xfinaudio.audio.spectral_profile import SpectralProfile, analyze_spectral_profile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DIR = PROJECT_ROOT / "assets" / "synthetic_color_tests"


def _generate_sine_wave(
    frequency: float,
    duration: float,
    sample_rate: int = 22050,
    amplitude: float = 0.5,
) -> bytes:
    samples = int(sample_rate * duration)
    data = bytearray()
    for i in range(samples):
        value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
        data.extend(value.to_bytes(2, "little", signed=True))
    return bytes(data)


def _generate_benchmark_folder(
    parent: Path,
    count: int,
    duration: float,
) -> Path:
    folder = parent / f"bench_{count}_{duration:.1f}s"
    folder.mkdir(parents=True, exist_ok=True)
    frequencies = [100.0, 500.0, 8000.0]
    for i in range(count):
        freq = frequencies[i % len(frequencies)]
        path = folder / f"tone_{i:04d}_{freq:.0f}hz.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(_generate_sine_wave(freq, duration))
    return folder


def _supported_audio_paths(folder: Path) -> list[Path]:
    suffixes = {".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"}
    return sorted(path for path in folder.rglob("*") if path.suffix.casefold() in suffixes)


def _median(values: Sequence[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def _run_sequential(
    paths: Sequence[Path],
    repetitions: int = 3,
    warm_up: bool = False,
) -> dict[str, Any]:
    if warm_up:
        for path in paths:
            analyze_spectral_profile(path)
    times: list[float] = []
    profiles: dict[str, SpectralProfile | None] = {}
    for _ in range(repetitions):
        start = time.perf_counter()
        for path in paths:
            profiles[str(path)] = analyze_spectral_profile(path)
        times.append(time.perf_counter() - start)
    return {
        "config": "sequential",
        "repetitions": repetitions,
        "median_seconds": _median(times),
        "throughput_tracks_per_second": len(paths) / _median(times) if _median(times) else 0.0,
        "total_tracks": len(paths),
        "profiles": {
            path: (profile.dominant_color if profile is not None else None) for path, profile in profiles.items()
        },
    }


def _run_parallel(
    paths: Sequence[Path],
    repetitions: int = 3,
    max_workers: int | None = None,
    warm_up: bool = False,
) -> dict[str, Any]:
    if warm_up:
        analyze_paths(list(paths), max_workers=max_workers)
    times: list[float] = []
    profiles: dict[str, SpectralProfile | None] = {}
    for _ in range(repetitions):
        start = time.perf_counter()
        profiles = analyze_paths(list(paths), max_workers=max_workers)
        times.append(time.perf_counter() - start)
    return {
        "config": "parallel",
        "repetitions": repetitions,
        "max_workers": max_workers,
        "median_seconds": _median(times),
        "throughput_tracks_per_second": len(paths) / _median(times) if _median(times) else 0.0,
        "total_tracks": len(paths),
        "profiles": {
            path: (profile.dominant_color if profile is not None else None) for path, profile in profiles.items()
        },
    }


def _run_thread(
    paths: Sequence[Path],
    repetitions: int = 3,
    max_workers: int | None = None,
    warm_up: bool = False,
) -> dict[str, Any]:
    if warm_up:
        analyze_paths(list(paths), max_workers=max_workers, executor="thread")
    times: list[float] = []
    profiles: dict[str, SpectralProfile | None] = {}
    for _ in range(repetitions):
        start = time.perf_counter()
        profiles = analyze_paths(list(paths), max_workers=max_workers, executor="thread")
        times.append(time.perf_counter() - start)
    return {
        "config": "thread",
        "repetitions": repetitions,
        "max_workers": max_workers,
        "median_seconds": _median(times),
        "throughput_tracks_per_second": len(paths) / _median(times) if _median(times) else 0.0,
        "total_tracks": len(paths),
        "profiles": {
            path: (profile.dominant_color if profile is not None else None) for path, profile in profiles.items()
        },
    }


def _run_cached(
    paths: Sequence[Path],
    repetitions: int = 3,
    max_workers: int | None = None,
    warm_up: bool = False,
) -> dict[str, Any]:
    cache: dict[str, tuple[int, int, SpectralProfile]] = {}
    if warm_up:
        analyze_paths(list(paths), max_workers=max_workers, executor="thread", cache=cache)
    times: list[float] = []
    profiles: dict[str, SpectralProfile | None] = {}
    for _ in range(repetitions):
        cache.clear()
        start = time.perf_counter()
        profiles = analyze_paths(list(paths), max_workers=max_workers, executor="thread", cache=cache)
        times.append(time.perf_counter() - start)
    return {
        "config": "cached",
        "repetitions": repetitions,
        "max_workers": max_workers,
        "median_seconds": _median(times),
        "throughput_tracks_per_second": len(paths) / _median(times) if _median(times) else 0.0,
        "total_tracks": len(paths),
        "profiles": {
            path: (profile.dominant_color if profile is not None else None) for path, profile in profiles.items()
        },
    }


def _run_cached_rescan(
    paths: Sequence[Path],
    repetitions: int = 3,
    max_workers: int | None = None,
    warm_up: bool = False,
) -> dict[str, Any]:
    cache: dict[str, tuple[int, int, SpectralProfile]] = {}
    analyze_paths(list(paths), max_workers=max_workers, executor="thread", cache=cache)
    if warm_up:
        analyze_paths(list(paths), max_workers=max_workers, executor="thread", cache=cache)
    times: list[float] = []
    profiles: dict[str, SpectralProfile | None] = {}
    for _ in range(repetitions):
        start = time.perf_counter()
        profiles = analyze_paths(list(paths), max_workers=max_workers, executor="thread", cache=cache)
        times.append(time.perf_counter() - start)
    return {
        "config": "cached-rescan",
        "repetitions": repetitions,
        "max_workers": max_workers,
        "median_seconds": _median(times),
        "throughput_tracks_per_second": len(paths) / _median(times) if _median(times) else 0.0,
        "total_tracks": len(paths),
        "profiles": {
            path: (profile.dominant_color if profile is not None else None) for path, profile in profiles.items()
        },
    }


def _render_markdown(report: dict[str, Any], output_path: Path) -> None:
    lines: list[str] = [
        "# Spectral Analysis Optimization Benchmark",
        "",
        f"**Folder:** `{report.get('folder')}`",
        f"**Tracks:** {report.get('total_tracks')}",
        f"**Duration per track:** {report.get('duration_seconds', 'n/a')}s",
        f"**Timestamp:** {report.get('timestamp')}",
        "",
        "| Config | Median seconds | Throughput (tracks/sec) | Notes |",
        "|---|---|---|---|",
    ]
    baseline = next(
        (result for result in report["results"] if result["config"] == "sequential"),
        None,
    )
    baseline_throughput = baseline.get("throughput_tracks_per_second", 0.0) if baseline else 0.0
    for result in report["results"]:
        config = result["config"]
        median = result.get("median_seconds", "—")
        throughput = result.get("throughput_tracks_per_second", "—")
        if isinstance(median, float):
            median = f"{median:.3f}"
        if isinstance(throughput, float):
            throughput = f"{throughput:.2f}"
        notes = ""
        if config != "sequential" and isinstance(throughput, str) and baseline_throughput:
            try:
                speedup = float(throughput) / baseline_throughput if baseline_throughput else 0.0
                notes = f"{speedup:.2f}× vs sequential"
            except ValueError:
                pass
        if "error" in result:
            notes = f"error: {result['error']}"
        lines.append(f"| {config} | {median} | {throughput} | {notes} |")
    lines.append("")
    lines.append("## Accuracy check")
    baseline_profiles = baseline.get("profiles", {}) if baseline else {}
    for result in report["results"]:
        if result["config"] == "sequential":
            continue
        profiles = result.get("profiles", {})
        mismatches = sum(1 for path, color in baseline_profiles.items() if profiles.get(path) != color)
        lines.append(f"- **{result['config']}**: {mismatches} dominant-color mismatches vs sequential")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark spectral analysis configurations.")
    parser.add_argument(
        "--folder",
        type=Path,
        default=None,
        help="Directory containing audio files to analyze (default: synthetic fixtures)",
    )
    parser.add_argument(
        "--generate",
        type=int,
        default=None,
        help="Generate N temporary sine-wave files for benchmarking",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Duration in seconds for generated files (default: 5.0)",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Number of repetitions per configuration",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Max workers for parallel/cached configurations",
    )
    parser.add_argument(
        "--warm-up",
        action="store_true",
        help="Run one warm-up pass before measuring",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        choices=["sequential", "parallel", "thread", "cached", "cached-rescan"],
        default=["sequential", "parallel", "thread", "cached", "cached-rescan"],
        help="Configurations to benchmark",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=PROJECT_ROOT / "openspec" / "changes" / "spectral-color-features" / "optimization-benchmark.json",
        help="Path for JSON report",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=PROJECT_ROOT / "openspec" / "changes" / "spectral-color-features" / "optimization-benchmark.md",
        help="Path for Markdown report",
    )
    args = parser.parse_args(argv)

    if args.folder is not None:
        folder = args.folder.resolve()
    elif args.generate is not None:
        temp_dir = tempfile.mkdtemp(prefix="xfinaudio_spectral_bench_")
        folder = _generate_benchmark_folder(Path(temp_dir), args.generate, args.duration)
    else:
        folder = SYNTHETIC_DIR

    paths = _supported_audio_paths(folder)
    if not paths:
        print(f"No supported audio files found in {folder}")
        return 1

    config_runners = {
        "sequential": lambda: _run_sequential(paths, args.repetitions, args.warm_up),
        "parallel": lambda: _run_parallel(paths, args.repetitions, args.max_workers, args.warm_up),
        "thread": lambda: _run_thread(paths, args.repetitions, args.max_workers, args.warm_up),
        "cached": lambda: _run_cached(paths, args.repetitions, args.max_workers, args.warm_up),
        "cached-rescan": lambda: _run_cached_rescan(paths, args.repetitions, args.max_workers, args.warm_up),
    }
    results: list[dict[str, Any]] = []
    for config in args.configs:
        print(f"Running {config} ...")
        results.append(config_runners[config]())

    report: dict[str, Any] = {
        "folder": str(folder),
        "total_tracks": len(paths),
        "duration_seconds": args.duration if args.generate else None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repetitions": args.repetitions,
        "max_workers": args.max_workers,
        "warm_up": args.warm_up,
        "results": results,
    }

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _render_markdown(report, args.markdown_output)
    print(f"JSON report: {args.json_output}")
    print(f"Markdown report: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
