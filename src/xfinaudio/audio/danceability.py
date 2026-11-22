"""Measured danceability, computed from the audio rather than read from a tag.

The `DANCEABILITY` tag Mixed In Key writes disagrees with its own comment field
on a large share of the library, so neither is trusted as a scoring input. This
module derives the value from the signal instead.

Three measurements, in the order they matter:

`pulse_clarity` is the height of the strongest peak in the autocorrelation of
the onset envelope. It answers "is there a beat", and it is the dominant term:
on its own it already separates peak-time house from classical with a Cohen's d
of 2.5, measured against a hand-labelled sample of the library.

`tempo_confidence` is how much of the onset energy the dominant tempo explains.
It saturates at 1.0 for anything with a steady beat, so it grades nothing at the
top -- it earns its place at the bottom, where it pushes rubato and free-time
material down.

`percussive_ratio` is the fraction of spectral energy that survives harmonic
separation. Clarity and tempo alone rank a pitched ostinato -- a film-score
riff, an arpeggiated synth line -- above real house, because those figures are
every bit as periodic as a drum machine. They are simply not percussive. The
gate is what makes the number mean "danceable" instead of "periodic", and it is
what takes the three-term score to a Cohen's d of 8.0 with no overlap at all
between the danceable and non-danceable groups.
"""

from __future__ import annotations

import logging
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pydantic import BaseModel, ConfigDict, Field

LOGGER = logging.getLogger(__name__)

CURRENT_DANCEABILITY_VERSION = 1

_SAMPLE_RATE = 22050
# Long enough to hold ~90 bars at house tempo, so the autocorrelation has
# several repetitions of the pattern to lock onto; short enough that a full
# library pass stays affordable.
_ANALYSIS_WINDOW_SECONDS = 45.0
_N_FFT = 2048
_HOP_LENGTH = 512

# Autocorrelation lags searched for the beat period. At 22050 Hz with hop 512
# the frame rate is ~43 Hz, so lag 8 is ~186 ms (320 BPM) and lag 200 is ~4.6 s.
_MIN_BEAT_LAG = 8
_MAX_BEAT_LAG = 200

# Percussive fractions measured on the library: pitched ostinati and orchestral
# material land near 0.20-0.29, grooves at 0.47-0.66. Below the floor the gate
# closes completely; above the ceiling it is fully open and stops interfering.
_PERCUSSIVE_FLOOR = 0.30
_PERCUSSIVE_CEILING = 0.52

# librosa.decompose.hpss defaults, reproduced here: a 31-frame median along each
# axis, then squared soft masks normalized against the larger of the two
# medians. HPSS is ~90% of the analyzer's per-track cost and all of it is these
# two median filters, which is why they are computed here, from the magnitude
# alone and in parallel blocks.
_HPSS_KERNEL = 31
_HPSS_POWER = 2.0
# At most two profile workers run at once (headless/profiles.py), so half the
# cores each keeps one library pass inside the machine instead of thrashing it.
_MAX_HPSS_WORKERS = 4
# Selecting the median needs a contiguous window view, so rows are filtered in
# batches that keep one thread's window buffer a few megabytes wide.
_MEDIAN_BATCH_WINDOWS = 1_000_000

# librosa emits these on every load that falls back from soundfile to audioread.
for _noisy_message in (
    r".*PySoundFile failed.*",
    r".*__audioread_load.*",
    r".*audioread.*[Dd]eprecated.*",
):
    warnings.filterwarnings("ignore", message=_noisy_message)


class DanceabilityProfile(BaseModel):
    """Measured rhythmic danceability for a single audio file."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0.0, le=1.0)
    pulse_clarity: float = Field(ge=0.0, le=1.0)
    tempo_confidence: float = Field(ge=0.0, le=1.0)
    percussive_ratio: float = Field(ge=0.0, le=1.0)
    analysis_version: int = Field(default=CURRENT_DANCEABILITY_VERSION, ge=1)


def analyze_danceability(path: Path | str) -> DanceabilityProfile | None:
    """Return a measured danceability profile for ``path``.

    Returns ``None`` when the file cannot be read, the audio dependency is
    unavailable, the excerpt is silent, or it is too short to measure. Audio
    with a pulse too weak to score returns 0.0, not ``None``: that is a
    measurement, not a failure. The source file is never modified.

    Analysis uses a 45-second window centered on the track middle, matching
    ``analyze_spectral_profile`` so both features describe the same excerpt.
    """
    try:
        import librosa
    except Exception as exc:
        LOGGER.warning("Danceability analysis unavailable for %s: %s: %s", path, type(exc).__name__, exc)
        return None

    try:
        audio_path = Path(path)
        if not audio_path.is_file():
            # A missing file must never reach librosa: soundfile fails first and
            # librosa falls back to audioread, whose aifc/audioop/sunau imports
            # are deprecated for removal in Python 3.13 and dropped in librosa
            # 1.0. Fail fast on the same None contract as the except below.
            return None
        try:
            track_duration = float(librosa.get_duration(path=audio_path))
        except Exception as exc:
            LOGGER.warning("Danceability duration probe failed for %s: %s: %s", audio_path, type(exc).__name__, exc)
            track_duration = None
        offset = 0.0
        if track_duration is not None and track_duration > _ANALYSIS_WINDOW_SECONDS:
            offset = max(0.0, (track_duration / 2.0) - (_ANALYSIS_WINDOW_SECONDS / 2.0))
        y, sr = librosa.load(
            audio_path,
            sr=_SAMPLE_RATE,
            mono=True,
            offset=offset,
            duration=_ANALYSIS_WINDOW_SECONDS,
        )
        if y.size == 0 and offset > 0.0:
            # Truncated files can declare a header duration longer than the real
            # stream, so a mid-track seek lands past EOF. Read from the start.
            y, sr = librosa.load(audio_path, sr=_SAMPLE_RATE, mono=True, duration=_ANALYSIS_WINDOW_SECONDS)
        if y.size == 0 or not np.any(y):
            return None

        onset_envelope = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
        if onset_envelope.size < _MAX_BEAT_LAG:
            # Too short to hold enough beat periods to autocorrelate against.
            return None
        # A signal with no onsets at all -- a held tone, a drone -- is not a
        # failed analysis. It is a measured zero, and every component below
        # already returns 0.0 for it. Reporting None instead would let the
        # scorer treat "definitely not danceable" as "unknown".

        pulse_clarity = _pulse_clarity(onset_envelope, librosa)
        tempo_confidence = _tempo_confidence(onset_envelope, sr, librosa)
        percussive_ratio = _percussive_ratio(y, librosa)

        gate = np.clip(
            (percussive_ratio - _PERCUSSIVE_FLOOR) / (_PERCUSSIVE_CEILING - _PERCUSSIVE_FLOOR),
            0.0,
            1.0,
        )
        score = float(np.clip(pulse_clarity * tempo_confidence * gate, 0.0, 1.0))
        return DanceabilityProfile(
            score=score,
            pulse_clarity=pulse_clarity,
            tempo_confidence=tempo_confidence,
            percussive_ratio=percussive_ratio,
            analysis_version=CURRENT_DANCEABILITY_VERSION,
        )
    except Exception as exc:
        LOGGER.warning("Danceability analysis failed for %s: %s: %s", path, type(exc).__name__, exc)
        return None


def _pulse_clarity(onset_envelope: np.ndarray, librosa) -> float:  # noqa: ANN001
    """Strength of the dominant periodicity in the onset envelope."""
    centered = onset_envelope - onset_envelope.mean()
    autocorrelation = librosa.autocorrelate(centered, max_size=len(centered) // 2)
    zero_lag = float(autocorrelation[0])
    if zero_lag <= 0:
        return 0.0
    normalized = autocorrelation / zero_lag
    upper = min(len(normalized) - 1, _MAX_BEAT_LAG)
    if upper <= _MIN_BEAT_LAG:
        return 0.0
    return float(np.clip(np.max(normalized[_MIN_BEAT_LAG:upper]), 0.0, 1.0))


def _tempo_confidence(onset_envelope: np.ndarray, sample_rate: float, librosa) -> float:  # noqa: ANN001
    """How much of the onset energy the dominant tempo accounts for."""
    tempogram = librosa.feature.tempogram(onset_envelope=onset_envelope, sr=sample_rate, hop_length=_HOP_LENGTH).mean(
        axis=1
    )
    peak = float(tempogram.max())
    if peak <= 0:
        return 0.0
    # Drop the first bins: they hold the zero-lag self-similarity every signal
    # has, danceable or not, and would float the score for silence-like input.
    profile = (tempogram / peak)[4:]
    if profile.size == 0:
        return 0.0
    dominant = float(profile.max())
    mean = float(profile.mean())
    if mean <= 0:
        return 0.0
    # Squared over the mean: a sharp single peak scores far above a flat
    # profile with the same maximum. The /4 puts a clean 4/4 grid at 1.0.
    return float(np.clip(dominant * (dominant / mean) / 4.0, 0.0, 1.0))


def _hpss_workers() -> int:
    """Threads for the median filters: bounded, and never zero."""
    return min(_MAX_HPSS_WORKERS, max(1, (os.cpu_count() or 1) // 2))


def _blocks(length: int, parts: int) -> list[tuple[int, int]]:
    """Contiguous ``[start, stop)`` ranges covering ``length`` in ``parts`` pieces."""
    if parts <= 1 or length <= 1:
        return [(0, length)]
    step = -(-length // parts)
    return [(start, min(start + step, length)) for start in range(0, length, step)]


def _median_rows(rows: np.ndarray) -> np.ndarray:
    """Median-filter every row along its last axis, ``_HPSS_KERNEL`` frames wide."""
    half = _HPSS_KERNEL // 2
    out = np.empty_like(rows)
    batch = max(1, _MEDIAN_BATCH_WINDOWS // max(1, rows.shape[-1] * _HPSS_KERNEL))
    for start in range(0, rows.shape[0], batch):
        stop = min(start + batch, rows.shape[0])
        # Symmetric padding is scipy's mode="reflect" as librosa uses it: index -1
        # reads element 0, -2 reads element 1, and so on. A median of an odd
        # window is one of its own elements, so the k-th selection is exact.
        padded = np.pad(rows[start:stop], ((0, 0), (half, half)), mode="symmetric")
        windows = sliding_window_view(padded, _HPSS_KERNEL, axis=-1)
        out[start:stop] = np.partition(windows, half, axis=-1)[..., half]
    return out


def _median_block(magnitude: np.ndarray, axis: int, start: int, stop: int) -> np.ndarray:
    """Median along ``axis`` over one block of the axis the kernel does not touch.

    A median is local, so the block of the other axis is independent: filtering
    blocks separately and pasting them back gives the whole-array result, which
    the equivalence test asserts against ``scipy.ndimage.median_filter``.

    ``axis=1`` filters along time and returns ``(stop - start, frames)``;
    ``axis=0`` filters along frequency and returns ``(frames, stop - start)``,
    already transposed so the median axis is the last one.
    """
    if axis == 1:
        return _median_rows(magnitude[start:stop, :])
    return _median_rows(np.ascontiguousarray(magnitude[:, start:stop].T))


def _hpss_median_magnitudes(magnitude: np.ndarray, *, workers: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """The two median-filtered magnitudes librosa's HPSS masks are built from."""
    workers = _hpss_workers() if workers is None else max(1, int(workers))
    harmonic = np.empty_like(magnitude)
    percussive = np.empty_like(magnitude)
    jobs = [(axis, start, stop) for axis in (1, 0) for start, stop in _blocks(magnitude.shape[1 - axis], workers)]

    def place(axis: int, start: int, stop: int, values: np.ndarray) -> None:
        if axis == 1:
            harmonic[start:stop, :] = values
        else:
            percussive[:, start:stop] = values.T

    if min(workers, len(jobs)) <= 1:
        for axis, start, stop in jobs:
            place(axis, start, stop, _median_block(magnitude, axis, start, stop))
        return harmonic, percussive
    with ThreadPoolExecutor(max_workers=min(workers, len(jobs)), thread_name_prefix="xfinaudio-hpss") as pool:
        futures = [(job, pool.submit(_median_block, magnitude, *job)) for job in jobs]
        for (axis, start, stop), future in futures:
            place(axis, start, stop, future.result())
    return harmonic, percussive


def _percussive_ratio(y: np.ndarray, librosa, *, workers: int | None = None) -> float:  # noqa: ANN001
    """Fraction of spectral energy that is transient rather than pitched.

    Same arithmetic as ``librosa.decompose.hpss``: the soft masks normalize each
    median against the larger of the two, so the phase librosa multiplies back in
    cancels out of ``|harmonic| + |percussive|``. Only the magnitude and the two
    masks are needed, which drops the complex products and their copies.
    """
    magnitude = np.abs(librosa.stft(y, n_fft=_N_FFT, hop_length=_HOP_LENGTH))
    harmonic, percussive = _hpss_median_magnitudes(magnitude, workers=workers)
    percussive_mask = librosa.util.softmask(percussive, harmonic, power=_HPSS_POWER, split_zeros=True)
    harmonic_mask = librosa.util.softmask(harmonic, percussive, power=_HPSS_POWER, split_zeros=True)
    percussive_energy = float(np.sum(magnitude * percussive_mask))
    harmonic_energy = float(np.sum(magnitude * harmonic_mask))
    total = percussive_energy + harmonic_energy
    if total <= 0:
        return 0.0
    return float(np.clip(percussive_energy / total, 0.0, 1.0))


__all__ = [
    "CURRENT_DANCEABILITY_VERSION",
    "DanceabilityProfile",
    "analyze_danceability",
]
