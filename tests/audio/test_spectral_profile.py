"""Tests for the read-only spectral color analyzer."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.audio.spectral_profile import (
    SpectralProfile,
    analyze_spectral_profile,
    score_spectral_similarity,
)

SYNTHETIC_DIR = Path(__file__).resolve().parents[2] / "assets" / "synthetic_color_tests"


def test_analyze_spectral_profile_classifies_synthetic_red() -> None:
    path = SYNTHETIC_DIR / "red_100hz.wav"

    profile = analyze_spectral_profile(path)

    assert profile is not None
    assert profile.dominant_color == "RED"
    assert profile.red_ratio > 0.8


def test_analyze_spectral_profile_classifies_synthetic_green() -> None:
    path = SYNTHETIC_DIR / "green_500hz.wav"

    profile = analyze_spectral_profile(path)

    assert profile is not None
    assert profile.dominant_color == "GREEN"
    assert profile.green_ratio > 0.8


def test_analyze_spectral_profile_classifies_synthetic_blue() -> None:
    path = SYNTHETIC_DIR / "blue_8000hz.wav"

    profile = analyze_spectral_profile(path)

    assert profile is not None
    assert profile.dominant_color == "BLUE"
    assert profile.blue_ratio > 0.8


def test_score_spectral_similarity_is_high_for_same_dominant_color() -> None:
    red = SpectralProfile(red_ratio=0.9, green_ratio=0.08, blue_ratio=0.02, dominant_color="RED")
    another_red = SpectralProfile(red_ratio=0.85, green_ratio=0.1, blue_ratio=0.05, dominant_color="RED")

    score = score_spectral_similarity(red, another_red)

    assert score > 0.7


def test_score_spectral_similarity_is_low_for_different_dominant_colors() -> None:
    red = SpectralProfile(red_ratio=0.9, green_ratio=0.08, blue_ratio=0.02, dominant_color="RED")
    green = SpectralProfile(red_ratio=0.05, green_ratio=0.9, blue_ratio=0.05, dominant_color="GREEN")

    score = score_spectral_similarity(red, green)

    assert score < 0.5


def test_analyze_spectral_profile_returns_none_for_missing_file() -> None:
    profile = analyze_spectral_profile(Path("/nonexistent/file.wav"))

    assert profile is None
