"""Tests for batch spectral analysis dispatch."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.audio import batch_analyzer
from xfinaudio.audio.batch_analyzer import _default_max_workers_for_analysis, analyze_paths


def test_default_max_workers_for_analysis_reserves_one_cpu() -> None:
    assert _default_max_workers_for_analysis(cpu_count=8) == 7
    assert _default_max_workers_for_analysis(cpu_count=1) == 1


def test_analyze_paths_uses_cpu_reservation_default(monkeypatch) -> None:
    captured: dict[str, int] = {}

    def fake_run_parallel(
        paths: list[Path],
        results: dict[str, object],
        cache: object,
        max_workers: int,
        on_progress: object,
        cancellation_token: object,
        use_threads: bool = True,
    ) -> None:
        captured["max_workers"] = max_workers
        for path in paths:
            results[str(path)] = None

    monkeypatch.setattr(batch_analyzer.os, "cpu_count", lambda: 8)
    monkeypatch.setattr(batch_analyzer, "_run_parallel", fake_run_parallel)

    analyze_paths([Path("/music/a.flac"), Path("/music/b.flac")])

    assert captured["max_workers"] == 7


def test_analyze_paths_respects_explicit_max_workers(monkeypatch) -> None:
    captured: dict[str, int] = {}

    def fake_run_parallel(
        paths: list[Path],
        results: dict[str, object],
        cache: object,
        max_workers: int,
        on_progress: object,
        cancellation_token: object,
        use_threads: bool = True,
    ) -> None:
        captured["max_workers"] = max_workers
        for path in paths:
            results[str(path)] = None

    monkeypatch.setattr(batch_analyzer.os, "cpu_count", lambda: 8)
    monkeypatch.setattr(batch_analyzer, "_run_parallel", fake_run_parallel)

    analyze_paths([Path("/music/a.flac"), Path("/music/b.flac")], max_workers=3)

    assert captured["max_workers"] == 3
