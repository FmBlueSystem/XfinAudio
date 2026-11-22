"""Equivalence contract for the danceability speed work (spec S2).

The HPSS stage of ``analyze_danceability`` is ~90% of the per-track cost, and all
of it was spent inside two median filters. The rewrite keeps exactly the
arithmetic ``librosa.decompose.hpss`` performs -- the same two median filters,
the same soft masks, the same energies -- and changes only *how* it is computed:
from the magnitude alone (the phase cancels) and split into contiguous blocks
that run on a bounded thread pool.

S2 says no stored value may move by more than 1e-6 absolute and the version must
not change, so these tests pin both halves of that promise:

* the block-split, multi-threaded median filter is bit-identical to the
  whole-array ``scipy.ndimage.median_filter`` librosa calls, at any worker count;
* ``percussive_ratio`` stays within 1e-6 of the librosa HPSS path it replaces,
  and a full ``analyze_danceability`` call still matches that path field by field.

The reference implementation below is the pre-change code, on purpose: it is the
differential check that the speedup preserves the measurement.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.io import wavfile
from scipy.ndimage import median_filter

from xfinaudio.audio import danceability

SAMPLE_RATE = 22050
# The analyzer needs more than ``_MAX_BEAT_LAG`` onset frames, so the full
# pipeline is measured on a longer excerpt than the ratio-only comparisons.
SECONDS = 4.0
PROFILE_SECONDS = 8.0
TOLERANCE = 1e-6
WORKERS = (1, 8)


def _groove(seconds: float = SECONDS) -> np.ndarray:
    """A kick on every beat: percussive, strictly periodic."""
    total = int(seconds * SAMPLE_RATE)
    out = np.zeros(total)
    period = int(SAMPLE_RATE * 60.0 / 128.0)
    kick_len = int(SAMPLE_RATE * 0.09)
    kick_t = np.arange(kick_len) / SAMPLE_RATE
    kick = np.sin(2.0 * np.pi * 55.0 * kick_t) * np.exp(-28.0 * kick_t)
    for start in range(0, total - period, period):
        out[start : start + kick_len] += kick
    return out


def _ostinato(seconds: float = SECONDS) -> np.ndarray:
    """A periodic melody with no percussion: only the percussive gate separates it."""
    total = int(seconds * SAMPLE_RATE)
    out = np.zeros(total)
    period = int(SAMPLE_RATE * 60.0 / 128.0)
    note_len = int(period * 0.9)
    t = np.arange(note_len) / SAMPLE_RATE
    envelope = np.minimum(1.0, t * 40.0) * np.exp(-1.5 * t)
    for index, start in enumerate(range(0, total - period, period)):
        frequency = 440.0 if index % 2 == 0 else 330.0
        out[start : start + note_len] += np.sin(2.0 * np.pi * frequency * t) * envelope
    return out


def _drone(seconds: float = SECONDS) -> np.ndarray:
    """One held note: no pulse at all, and the masks are dominated by harmonics."""
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return np.sin(2.0 * np.pi * 220.0 * t)


def _broadband(seconds: float = SECONDS) -> np.ndarray:
    """White noise: fills both median filters with non-degenerate magnitudes."""
    return np.random.default_rng(7).standard_normal(int(seconds * SAMPLE_RATE)) * 0.1


SIGNALS = {
    "groove": _groove,
    "ostinato": _ostinato,
    "drone": _drone,
    "broadband": _broadband,
}


def _signal(name: str, seconds: float = SECONDS) -> np.ndarray:
    return SIGNALS[name](seconds).astype(np.float32)


def _librosa_percussive_ratio(y: np.ndarray) -> float:
    """The pre-change implementation: complex hpss, then the energies of its parts."""
    import librosa

    stft = librosa.stft(y, n_fft=danceability._N_FFT, hop_length=danceability._HOP_LENGTH)  # noqa: SLF001
    harmonic, percussive = librosa.decompose.hpss(stft)
    percussive_energy = float(np.abs(percussive).sum())
    harmonic_energy = float(np.abs(harmonic).sum())
    total = percussive_energy + harmonic_energy
    return 0.0 if total <= 0 else float(np.clip(percussive_energy / total, 0.0, 1.0))


def _write(path, samples: np.ndarray) -> None:
    peak = float(np.max(np.abs(samples))) or 1.0
    wavfile.write(path, SAMPLE_RATE, (samples / peak * 0.9).astype(np.float32))


@pytest.mark.parametrize("workers", WORKERS)
@pytest.mark.parametrize("shape", [(37, 128), (129, 41), (33, 33), (5, 40), (64, 1), (1, 64)])
def test_block_median_matches_the_whole_array_median(shape: tuple[int, int], workers: int) -> None:
    """Splitting the untouched axis must not change one selected median value."""
    rng = np.random.default_rng(4)
    magnitude = (rng.random(shape, dtype=np.float32) ** 3).astype(np.float32)

    harmonic, percussive = danceability._hpss_median_magnitudes(magnitude, workers=workers)  # noqa: SLF001

    assert np.array_equal(harmonic, median_filter(magnitude, size=(1, 31), mode="reflect"))
    assert np.array_equal(percussive, median_filter(magnitude, size=(31, 1), mode="reflect"))


@pytest.mark.parametrize("workers", WORKERS)
@pytest.mark.parametrize("name", sorted(SIGNALS))
def test_percussive_ratio_matches_the_librosa_hpss_path(name: str, workers: int) -> None:
    import librosa

    y = _signal(name)

    expected = _librosa_percussive_ratio(y)
    measured = danceability._percussive_ratio(y, librosa, workers=workers)  # noqa: SLF001

    assert abs(measured - expected) < TOLERANCE


@pytest.mark.parametrize("cpus", [128, 8, 4, 3, 1, None])
def test_hpss_worker_count_is_bounded(cpus: int | None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The internal pool is bounded: never zero, and never one thread per core.

    Two profile workers are in flight at once, so an analysis may use at most
    half the cores; a single-core machine still gets one thread, not zero.
    """
    monkeypatch.setattr(danceability.os, "cpu_count", lambda: cpus)

    workers = danceability._hpss_workers()  # noqa: SLF001

    assert 1 <= workers <= danceability._MAX_HPSS_WORKERS  # noqa: SLF001
    if cpus is None:
        assert workers == 1
    else:
        assert workers == min(danceability._MAX_HPSS_WORKERS, max(1, cpus // 2))  # noqa: SLF001


def test_stored_version_did_not_move() -> None:
    """S2: a faster analyzer must not invalidate the profiles already on disk."""
    assert danceability.CURRENT_DANCEABILITY_VERSION == 1


@pytest.mark.parametrize("name", ["groove", "ostinato"])
def test_full_profile_matches_the_librosa_hpss_path(name: str, tmp_path) -> None:
    """The whole measurement, not just the ratio, stays within the S2 tolerance."""
    import librosa

    y = _signal(name, PROFILE_SECONDS)
    track = tmp_path / f"{name}.wav"
    _write(track, y)

    profile = danceability.analyze_danceability(track)

    assert profile is not None
    expected_ratio = _librosa_percussive_ratio(y)
    assert abs(profile.percussive_ratio - expected_ratio) < TOLERANCE
    # The three other fields are unchanged code paths, pinned so a future edit
    # cannot quietly move them while this test only watches the ratio.
    onset_envelope = librosa.onset.onset_strength(y=y, sr=SAMPLE_RATE, aggregate=np.median)
    pulse_clarity = danceability._pulse_clarity(onset_envelope, librosa)  # noqa: SLF001
    tempo_confidence = danceability._tempo_confidence(onset_envelope, SAMPLE_RATE, librosa)  # noqa: SLF001
    assert abs(profile.pulse_clarity - pulse_clarity) < TOLERANCE
    assert abs(profile.tempo_confidence - tempo_confidence) < TOLERANCE
    gate = np.clip(
        (expected_ratio - danceability._PERCUSSIVE_FLOOR)  # noqa: SLF001
        / (danceability._PERCUSSIVE_CEILING - danceability._PERCUSSIVE_FLOOR),  # noqa: SLF001
        0.0,
        1.0,
    )
    assert abs(profile.score - float(np.clip(pulse_clarity * tempo_confidence * gate, 0.0, 1.0))) < TOLERANCE
