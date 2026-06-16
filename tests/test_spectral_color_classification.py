"""Tests for the rebalanced spectral color classification (frequency-weighted, 0.45 threshold)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xfinaudio.audio.spectral_profile import _dominant_color, analyze_spectral_profile

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "synthetic_color_tests"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("subbass_50hz.wav", "RED"),
        ("red_100hz.wav", "RED"),
        ("green_500hz.wav", "GREEN"),
        ("blue_8000hz.wav", "BLUE"),
        ("veryhigh_12000hz.wav", "BLUE"),
    ],
)
def test_synthetic_tones_classify_to_their_band(filename: str, expected: str) -> None:
    asset = _ASSETS / filename
    if not asset.exists():
        pytest.skip(f"missing asset {filename}")
    profile = analyze_spectral_profile(asset)
    if profile is None:
        pytest.skip("librosa unavailable")
    assert profile.dominant_color == expected


def test_dominant_color_threshold_is_045() -> None:
    # A clear plurality at 0.45 wins; below it is MIXED.
    assert _dominant_color(0.46, 0.30, 0.24) == "RED"
    assert _dominant_color(0.44, 0.30, 0.26) == "MIXED"
    assert _dominant_color(0.10, 0.10, 0.80) == "BLUE"
