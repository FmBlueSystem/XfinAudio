"""Tests for the batch spectral analyzer."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.audio.batch_analyzer import analyze_paths
from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.scan_service import ScanCancellationToken

SYNTHETIC_DIR = Path(__file__).resolve().parents[2] / "assets" / "synthetic_color_tests"


def test_batch_analyzer_returns_same_results_as_sequential() -> None:
    paths = [
        SYNTHETIC_DIR / "red_100hz.wav",
        SYNTHETIC_DIR / "green_500hz.wav",
        SYNTHETIC_DIR / "blue_8000hz.wav",
    ]

    results = analyze_paths(paths)

    assert len(results) == 3
    assert results[str(paths[0])] is not None
    assert results[str(paths[0])].dominant_color == "RED"
    assert results[str(paths[1])].dominant_color == "GREEN"
    assert results[str(paths[2])].dominant_color == "BLUE"


def test_batch_analyzer_runs_analysis_when_cache_identity_mismatches(monkeypatch) -> None:
    path = SYNTHETIC_DIR / "red_100hz.wav"
    cached_profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        dominant_color="GREEN",
    )
    cache = {str(path): (0, 0, cached_profile)}

    called = False

    def fake_analyze(_path: Path) -> SpectralProfile:
        nonlocal called
        called = True
        return SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")

    monkeypatch.setattr("xfinaudio.audio.batch_analyzer.analyze_spectral_profile", fake_analyze)

    results = analyze_paths([path], cache=cache)

    assert called
    assert results[str(path)].dominant_color == "RED"


def test_batch_analyzer_uses_cached_profile_when_identity_matches(monkeypatch) -> None:
    path = SYNTHETIC_DIR / "red_100hz.wav"
    stat = path.stat()
    cached_profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        dominant_color="GREEN",
    )
    cache = {str(path): (stat.st_mtime_ns, stat.st_size, cached_profile)}

    called = False

    def fake_analyze(_path: Path) -> SpectralProfile:
        nonlocal called
        called = True
        return SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")

    monkeypatch.setattr("xfinaudio.audio.batch_analyzer.analyze_spectral_profile", fake_analyze)

    results = analyze_paths([path], cache=cache)

    assert not called
    assert results[str(path)] == cached_profile


def test_batch_analyzer_respects_cancellation() -> None:
    paths = [
        SYNTHETIC_DIR / "red_100hz.wav",
        SYNTHETIC_DIR / "green_500hz.wav",
        SYNTHETIC_DIR / "blue_8000hz.wav",
    ]
    token = ScanCancellationToken()
    token.cancel()

    results = analyze_paths(paths, cancellation_token=token)

    assert results == {}


def test_batch_analyzer_emits_progress_for_every_path() -> None:
    paths = [
        SYNTHETIC_DIR / "red_100hz.wav",
        SYNTHETIC_DIR / "green_500hz.wav",
        SYNTHETIC_DIR / "blue_8000hz.wav",
    ]
    progress_paths: list[Path] = []

    analyze_paths(paths, on_progress=progress_paths.append)

    assert sorted(progress_paths) == sorted(paths)


def test_batch_analyzer_returns_empty_for_empty_input() -> None:
    assert analyze_paths([]) == {}


def test_batch_analyzer_sequential_executor_ignores_max_workers(monkeypatch) -> None:
    path = SYNTHETIC_DIR / "red_100hz.wav"

    called = False

    def fake_analyze(_path: Path) -> SpectralProfile:
        nonlocal called
        called = True
        return SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")

    monkeypatch.setattr("xfinaudio.audio.batch_analyzer.analyze_spectral_profile", fake_analyze)

    analyze_paths([path], executor="sequential")

    assert called
