"""Tests for the read-only danceability analyzer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from xfinaudio.audio.danceability import (
    CURRENT_DANCEABILITY_VERSION,
    DanceabilityProfile,
    analyze_danceability,
)

SAMPLE_RATE = 22050
DURATION_SECONDS = 20.0


def _write(path: Path, samples: np.ndarray) -> None:
    peak = float(np.max(np.abs(samples))) or 1.0
    wavfile.write(path, SAMPLE_RATE, (samples / peak * 0.9).astype(np.float32))


def _four_on_the_floor(bpm: float = 128.0) -> np.ndarray:
    """A kick every beat plus offbeat hats: transient-driven and strictly periodic."""
    total = int(DURATION_SECONDS * SAMPLE_RATE)
    out = np.zeros(total)
    period = int(SAMPLE_RATE * 60.0 / bpm)
    kick_len = int(SAMPLE_RATE * 0.09)
    kick_t = np.arange(kick_len) / SAMPLE_RATE
    kick = np.sin(2.0 * np.pi * 55.0 * kick_t) * np.exp(-28.0 * kick_t)
    hat_len = int(SAMPLE_RATE * 0.03)
    rng = np.random.default_rng(0)
    hat = rng.standard_normal(hat_len) * np.exp(-90.0 * np.arange(hat_len) / SAMPLE_RATE)
    for start in range(0, total - period, period):
        out[start : start + kick_len] += kick
        offbeat = start + period // 2
        if offbeat + hat_len < total:
            out[offbeat : offbeat + hat_len] += hat * 0.35
    return out


def _sustained_tone() -> np.ndarray:
    """One held note: no pulse at all."""
    t = np.arange(int(DURATION_SECONDS * SAMPLE_RATE)) / SAMPLE_RATE
    return np.sin(2.0 * np.pi * 220.0 * t)


def _pitched_ostinato() -> np.ndarray:
    """A strictly periodic melodic figure with no percussion.

    This is the case a pure periodicity measure gets wrong: the pulse is as
    regular as a drum machine, but nobody dances to it. Only the percussive
    gate separates it from a groove.
    """
    total = int(DURATION_SECONDS * SAMPLE_RATE)
    out = np.zeros(total)
    period = int(SAMPLE_RATE * 60.0 / 128.0)
    note_len = int(period * 0.9)
    t = np.arange(note_len) / SAMPLE_RATE
    envelope = np.minimum(1.0, t * 40.0) * np.exp(-1.5 * t)
    for index, start in enumerate(range(0, total - period, period)):
        frequency = 440.0 if index % 2 == 0 else 330.0
        out[start : start + note_len] += np.sin(2.0 * np.pi * frequency * t) * envelope
    return out


@pytest.fixture(scope="module")
def groove(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("danceability") / "groove.wav"
    _write(path, _four_on_the_floor())
    return path


@pytest.fixture(scope="module")
def drone(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("danceability") / "drone.wav"
    _write(path, _sustained_tone())
    return path


@pytest.fixture(scope="module")
def ostinato(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("danceability") / "ostinato.wav"
    _write(path, _pitched_ostinato())
    return path


def test_four_on_the_floor_scores_high(groove: Path) -> None:
    profile = analyze_danceability(groove)

    assert profile is not None
    assert profile.score > 0.6
    assert profile.pulse_clarity > 0.5
    assert profile.percussive_ratio > 0.3


def test_sustained_tone_scores_near_zero(drone: Path) -> None:
    profile = analyze_danceability(drone)

    assert profile is not None
    assert profile.score < 0.1


def test_pitched_ostinato_is_not_danceable(ostinato: Path) -> None:
    """Regression: periodicity alone ranked a pitched ostinato above real house."""
    profile = analyze_danceability(ostinato)

    assert profile is not None
    assert profile.percussive_ratio < 0.4
    assert profile.score < 0.4


def test_groove_outranks_both_non_danceable_cases(groove: Path, drone: Path, ostinato: Path) -> None:
    scores = {
        name: analyze_danceability(path)
        for name, path in (("groove", groove), ("drone", drone), ("ostinato", ostinato))
    }

    assert all(profile is not None for profile in scores.values())
    assert scores["groove"].score > scores["ostinato"].score
    assert scores["groove"].score > scores["drone"].score


def test_score_is_bounded_and_versioned(groove: Path) -> None:
    profile = analyze_danceability(groove)

    assert profile is not None
    assert 0.0 <= profile.score <= 1.0
    assert profile.analysis_version == CURRENT_DANCEABILITY_VERSION


def test_missing_file_returns_none(tmp_path: Path) -> None:
    assert analyze_danceability(tmp_path / "does_not_exist.wav") is None


def test_silence_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "silence.wav"
    wavfile.write(path, SAMPLE_RATE, np.zeros(SAMPLE_RATE * 5, dtype=np.float32))

    assert analyze_danceability(path) is None


def test_profile_rejects_out_of_range_score() -> None:
    with pytest.raises(ValueError):
        DanceabilityProfile(score=1.5, pulse_clarity=0.5, tempo_confidence=0.5, percussive_ratio=0.5)
