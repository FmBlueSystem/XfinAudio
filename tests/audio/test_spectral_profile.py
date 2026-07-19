"""Tests for the read-only spectral color analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from xfinaudio.audio.spectral_profile import (
    SpectralProfile,
    analyze_spectral_profile,
    dominant_color_for_ratios,
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


@pytest.mark.parametrize(
    ("ratios", "expected"),
    [
        ((0.45, 0.30, 0.25), "RED"),
        ((0.30, 0.45, 0.25), "GREEN"),
        ((0.40, 0.35, 0.25), "BLUE"),
        ((0.449, 0.449, 0.249), "MIXED"),
    ],
)
def test_dominant_color_uses_per_band_thresholds(ratios: tuple[float, float, float], expected: str) -> None:
    assert dominant_color_for_ratios(*ratios) == expected


def test_dominant_color_uses_largest_threshold_excess() -> None:
    assert dominant_color_for_ratios(0.50, 0.47, 0.03) == "RED"
    assert dominant_color_for_ratios(0.46, 0.48, 0.06) == "GREEN"
    assert dominant_color_for_ratios(0.46, 0.279, 0.261) == "BLUE"


@pytest.mark.parametrize(
    ("ratios", "expected"),
    [
        ((0.50, 0.50, 0.00), "RED"),
        ((0.50, 0.20, 0.30), "RED"),
        ((0.20, 0.50, 0.30), "GREEN"),
    ],
)
def test_dominant_color_exact_excess_ties_use_fixed_priority(ratios: tuple[float, float, float], expected: str) -> None:
    assert dominant_color_for_ratios(*ratios) == expected


def test_dominant_color_near_tie_uses_exact_largest_excess() -> None:
    assert dominant_color_for_ratios(0.5000001, 0.50, 0.0) == "RED"
    assert dominant_color_for_ratios(0.50, 0.5000001, 0.0) == "GREEN"
