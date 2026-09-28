"""Tests for the read-only tonal interval profiling (TIV) analyzer.

All math is exercised on synthetic vectors; the single integration test uses a
short synthesized tone so no real audio asset is required.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from scipy.io import wavfile

from xfinaudio.audio.analyzer import LibrosaTonalAnalyzer, TonalAnalyzer
from xfinaudio.audio.tonal_profile import (
    CURRENT_TONAL_VERSION,
    TIV_DIMENSIONS,
    TonalProfile,
    _chroma_to_tiv,
    analyze_tonal_profile,
    tiv_compatibility,
)


def _tonal(tiv: tuple[float, float, float, float, float, float], *, coherence: float = 0.5) -> TonalProfile:
    return TonalProfile(tiv=tiv, tonal_coherence=coherence)


def _write_tone(path: Path, *, seconds: float = 5.0, frequency: float = 440.0, sample_rate: int = 8000) -> None:
    samples = np.sin(2.0 * np.pi * frequency * np.arange(int(seconds * sample_rate)) / sample_rate)
    wavfile.write(path, sample_rate, samples.astype(np.float32))


def test_current_tonal_version_is_one() -> None:
    assert CURRENT_TONAL_VERSION == 1


def test_tonal_profile_defaults_to_current_version() -> None:
    profile = _tonal((0.1, 0.2, 0.3, 0.4, 0.5, 0.6), coherence=0.5)

    assert profile.analysis_version == CURRENT_TONAL_VERSION
    assert len(profile.tiv) == TIV_DIMENSIONS == 6


def test_tiv_compatibility_of_identical_vectors_is_one() -> None:
    vector = (0.5, 0.3, 0.1, 0.05, 0.03, 0.02)

    assert tiv_compatibility(_tonal(vector), _tonal(vector)) == pytest.approx(1.0)


def test_tiv_compatibility_of_orthogonal_components_is_low() -> None:
    left = _tonal((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    right = _tonal((0.0, 1.0, 0.0, 0.0, 0.0, 0.0))

    assert tiv_compatibility(left, right) == pytest.approx(0.0)


def test_tiv_compatibility_ignores_magnitude_scale() -> None:
    left = _tonal((2.0, 0.0, 1.0, 0.0, 0.0, 1.0))
    right = _tonal((4.0, 0.0, 2.0, 0.0, 0.0, 2.0))

    assert tiv_compatibility(left, right) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "degenerate",
    [
        None,
        _tonal((0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
    ],
)
def test_tiv_compatibility_returns_none_for_degenerate_input(degenerate: TonalProfile | None) -> None:
    healthy = _tonal((0.5, 0.5, 0.0, 0.0, 0.0, 0.0))

    assert tiv_compatibility(degenerate, healthy) is None
    assert tiv_compatibility(healthy, degenerate) is None


def test_chroma_to_tiv_of_a_single_pitch_class_is_flat() -> None:
    chroma = np.zeros(12)
    chroma[0] = 1.0

    tiv = _chroma_to_tiv(chroma)

    assert tiv == pytest.approx((1.0, 1.0, 1.0, 1.0, 1.0, 1.0))


def test_chroma_to_tiv_of_a_uniform_chroma_is_zero() -> None:
    chroma = np.full(12, 1.0 / 12.0)

    tiv = _chroma_to_tiv(chroma)

    assert tiv == pytest.approx((0.0, 0.0, 0.0, 0.0, 0.0, 0.0), abs=1e-9)


def test_chroma_to_tiv_of_empty_chroma_is_zero() -> None:
    assert _chroma_to_tiv(np.zeros(12)) == pytest.approx((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))


def test_analyze_tonal_profile_returns_none_for_missing_file() -> None:
    assert analyze_tonal_profile(Path("/nonexistent/file.wav")) is None


def test_analyze_tonal_profile_missing_file_does_not_trigger_audioread_fallback() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        profile = analyze_tonal_profile(Path("/nonexistent/file.wav"))

    assert profile is None
    assert [str(w.message) for w in caught if "PySoundFile failed" in str(w.message)] == []


def test_analyze_tonal_profile_returns_none_when_decoding_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import librosa

    path = tmp_path / "tone.wav"
    _write_tone(path)

    def exploding_load(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("decoder exploded")

    monkeypatch.setattr(librosa, "load", exploding_load)

    assert analyze_tonal_profile(path) is None


def test_analyze_tonal_profile_returns_version_and_bounded_coherence(tmp_path: Path) -> None:
    path = tmp_path / "tone.wav"
    _write_tone(path)

    profile = analyze_tonal_profile(path)

    assert profile is not None
    assert profile.analysis_version == CURRENT_TONAL_VERSION
    assert 0.0 <= profile.tonal_coherence <= 1.0
    assert sum(profile.tiv) > 0.0


def test_librosa_tonal_analyzer_delegates_to_profile_function(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = _tonal((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    calls: list[Path] = []

    def fake_analyze(path: Path | str) -> TonalProfile:
        calls.append(Path(path))
        return expected

    monkeypatch.setattr("xfinaudio.audio.analyzer.analyze_tonal_profile", fake_analyze)

    analyzer: TonalAnalyzer = LibrosaTonalAnalyzer()

    assert analyzer.analyze(Path("/music/a.wav")) == expected
    assert calls == [Path("/music/a.wav")]
