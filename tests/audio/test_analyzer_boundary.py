"""Tests for the spectral analyzer adapter boundary."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.audio.analyzer import LibrosaSpectralAnalyzer, SpectralAnalyzer
from xfinaudio.audio.spectral_profile import SpectralProfile


def test_librosa_spectral_analyzer_delegates_to_existing_profile_function(monkeypatch) -> None:
    expected = SpectralProfile(red_ratio=1.0, green_ratio=0.0, blue_ratio=0.0, dominant_color="RED")
    calls: list[Path] = []

    def fake_analyze(path: Path | str) -> SpectralProfile:
        calls.append(Path(path))
        return expected

    monkeypatch.setattr("xfinaudio.audio.analyzer.analyze_spectral_profile", fake_analyze)

    analyzer: SpectralAnalyzer = LibrosaSpectralAnalyzer()

    assert analyzer.analyze(Path("/music/a.wav")) == expected
    assert calls == [Path("/music/a.wav")]
