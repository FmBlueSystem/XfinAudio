"""Tests for intro/outro spectral color analysis."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from scipy.io import wavfile

from xfinaudio.audio.spectral_profile import (
    CURRENT_EDGE_ANALYSIS_VERSION,
    EdgeSpectralProfile,
    analyze_edge_spectral_profile,
)


def _write_tone_sections(path: Path, sections: list[tuple[float, float]], *, sample_rate: int = 22050) -> None:
    samples = [
        np.sin(2.0 * np.pi * frequency * np.arange(int(duration * sample_rate)) / sample_rate)
        for duration, frequency in sections
    ]
    wavfile.write(path, sample_rate, np.concatenate(samples).astype(np.float32))


def test_edge_profile_analyzes_intro_and_outro_separately(tmp_path: Path) -> None:
    path = tmp_path / "red-intro-blue-outro.wav"
    _write_tone_sections(path, [(30.0, 100.0), (10.0, 500.0), (30.0, 8000.0)])

    profile = analyze_edge_spectral_profile(path)

    assert profile is not None
    assert profile.intro.dominant_color == "RED"
    assert profile.outro.dominant_color == "BLUE"


def test_edge_profile_ignores_contrasting_middle(tmp_path: Path) -> None:
    path = tmp_path / "contrasting-middle.wav"
    _write_tone_sections(path, [(30.0, 100.0), (15.0, 500.0), (30.0, 8000.0)])

    profile = analyze_edge_spectral_profile(path)

    assert profile is not None
    assert (profile.intro.dominant_color, profile.outro.dominant_color) == ("RED", "BLUE")


def test_edge_profile_returns_none_when_windows_would_overlap(tmp_path: Path) -> None:
    path = tmp_path / "too-short.wav"
    _write_tone_sections(path, [(30.0, 100.0), (30.0, 8000.0)])

    assert analyze_edge_spectral_profile(path) is None


def test_edge_profile_returns_none_for_missing_file_and_silence(tmp_path: Path) -> None:
    silent_path = tmp_path / "silence.wav"
    wavfile.write(silent_path, 22050, np.zeros(70 * 22050, dtype=np.float32))

    assert analyze_edge_spectral_profile(Path("/nonexistent/file.wav")) is None
    assert analyze_edge_spectral_profile(silent_path) is None


def test_edge_profile_missing_file_does_not_trigger_audioread_fallback() -> None:
    """A missing path must fail fast instead of entering the deprecated fallback.

    librosa warns "PySoundFile failed. Trying audioread instead." before raising.
    That fallback depends on aifc/audioop/sunau, removed in Python 3.13, so a
    missing file must never reach it. The module-level filters suppress this
    warning in production; ``simplefilter(\"always\")`` here neutralizes them so
    the guard observes the fallback even if it returns.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        profile = analyze_edge_spectral_profile(Path("/nonexistent/file.wav"))

    assert profile is None
    assert [str(w.message) for w in caught if "PySoundFile failed" in str(w.message)] == []


def test_edge_profile_uses_current_analysis_version(tmp_path: Path) -> None:
    path = tmp_path / "versioned.wav"
    _write_tone_sections(path, [(30.0, 100.0), (10.0, 500.0), (30.0, 8000.0)])

    profile = analyze_edge_spectral_profile(path)

    assert profile is not None
    assert profile.analysis_version == CURRENT_EDGE_ANALYSIS_VERSION == 1


def test_edge_profile_requires_both_edges() -> None:
    with pytest.raises(ValidationError):
        EdgeSpectralProfile(intro=None, outro=None)  # type: ignore[arg-type]
