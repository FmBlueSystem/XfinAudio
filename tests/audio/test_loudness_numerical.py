"""Independent EBU/ITU expectations; actual analyzer, synthetic PCM, no tag writes.

EBU Tech3341 Table1 cases1/2 and15–19; full compliance is not implied.
The default Linux developer FFmpeg is not certification of the macOS bundle.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import wave
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import pytest

from xfinaudio.audio.loudness import FfmpegLoudnessAdapter, LoudnessStatus


def _tone(seconds=20, rate=48000, level=-23, divisor=None, phase=0, amplitude=None):
    frequency = 1000 if divisor is None else rate / divisor
    gain = 10 ** (level / 20) if amplitude is None else amplitude
    x = gain * np.sin(2 * np.pi * frequency * np.arange(round(seconds * rate)) / rate + np.deg2rad(phase))
    if divisor is not None:
        taper = round(rate * 0.01)
        x[:taper] *= np.linspace(0, 1, taper)
        x[-taper:] *= np.linspace(1, 0, taper)
    return np.repeat(x[:, None], 2, axis=1)


def _measure(tmp_path, x, rate=48000):
    executable = os.environ.get("XFINAUDIO_FFMPEG_BINARY") or shutil.which("ffmpeg")
    if not executable:
        pytest.skip("requires actual bundled or developer FFmpeg")
    path = tmp_path / "synthetic.wav"
    pcm = np.rint(x * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm.tobytes())
    before = hashlib.sha256(path.read_bytes()).digest()
    profile = FfmpegLoudnessAdapter(Path(executable).resolve(), engine_fingerprint="synthetic-reference").analyze(
        path, duration_seconds=len(x) / rate
    )
    assert hashlib.sha256(path.read_bytes()).digest() == before
    return profile


@pytest.mark.parametrize("rate", [44100, 48000, 96000])
@pytest.mark.parametrize("level", [-23, -33])
def test_known_level_matches_ebu_and_independent_meter(tmp_path, rate, level):
    x = _tone(rate=rate, level=level)
    profile = _measure(tmp_path, x, rate)
    assert profile.lufs_integrated == pytest.approx(level, abs=0.1)
    assert profile.lufs_integrated == pytest.approx(pyln.Meter(rate).integrated_loudness(x), abs=0.1)
    assert profile.status is LoudnessStatus.TOO_SHORT
    assert profile.loudness_range_lra is None
    assert profile.true_peak_dbtp == pytest.approx(level, abs=0.1)


@pytest.mark.parametrize(
    "divisor,phase,amplitude,expected",
    [
        (4, 0, 0.5, -6),
        (4, 45, 0.5, -6),
        (6, 60, 0.5, -6),
        (8, 67.5, 0.5, -6),
        (4, 45, 1.41, 3),
    ],
)
def test_ebu_true_peak_includes_intersample_overload(tmp_path, divisor, phase, amplitude, expected):
    profile = _measure(tmp_path, _tone(5, divisor=divisor, phase=phase, amplitude=amplitude))
    assert profile.true_peak_dbtp is not None
    assert expected - 0.4 <= profile.true_peak_dbtp <= expected + 0.2


def test_relative_gate_and_current_complete_lra(tmp_path):
    x = np.concatenate([_tone(10, level=-36), _tone(60), _tone(10, level=-36)])
    profile = _measure(tmp_path, x)
    assert profile.status is LoudnessStatus.MEASURED
    assert profile.lufs_integrated == pytest.approx(-23, abs=0.1)
    assert profile.lufs_integrated == pytest.approx(pyln.Meter(48000).integrated_loudness(x), abs=0.1)


def test_lra_two_known_plateaus(tmp_path):
    profile = _measure(tmp_path, np.concatenate([_tone(30, level=-20), _tone(30, level=-30)]))
    assert profile.status is LoudnessStatus.MEASURED
    assert profile.loudness_range_lra == pytest.approx(10, abs=0.1)


@pytest.mark.parametrize("duration", [3, 3.3, 59.9, 60])
def test_constant_tone_never_reports_startup_lra_artifact(tmp_path, duration):
    profile = _measure(tmp_path, _tone(duration, level=-20))
    assert profile.lufs_integrated == pytest.approx(-20, abs=0.1)
    assert profile.true_peak_dbtp == pytest.approx(-20, abs=0.1)
    if duration < 60:
        assert profile.status is LoudnessStatus.TOO_SHORT
        assert profile.loudness_range_lra is None
    else:
        assert profile.status is LoudnessStatus.MEASURED
        assert profile.loudness_range_lra == pytest.approx(0, abs=0.1)


@pytest.mark.parametrize("level", [None, -80])
def test_silence_and_below_absolute_gate_are_not_measured(tmp_path, level):
    x = np.zeros((48000 * 5, 2)) if level is None else _tone(5, level=level)
    profile = _measure(tmp_path, x)
    assert profile.status is LoudnessStatus.UNMEASURABLE
    assert profile.lufs_integrated is None
