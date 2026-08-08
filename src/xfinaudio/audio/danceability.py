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

import warnings
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

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
    except Exception:
        return None

    try:
        audio_path = Path(path)
        try:
            track_duration = float(librosa.get_duration(path=audio_path))
        except Exception:
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
    except Exception:
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


def _percussive_ratio(y: np.ndarray, librosa) -> float:  # noqa: ANN001
    """Fraction of spectral energy that is transient rather than pitched."""
    stft = librosa.stft(y, n_fft=_N_FFT, hop_length=_HOP_LENGTH)
    harmonic, percussive = librosa.decompose.hpss(stft)
    percussive_energy = float(np.abs(percussive).sum())
    harmonic_energy = float(np.abs(harmonic).sum())
    total = percussive_energy + harmonic_energy
    if total <= 0:
        return 0.0
    return float(np.clip(percussive_energy / total, 0.0, 1.0))


__all__ = [
    "CURRENT_DANCEABILITY_VERSION",
    "DanceabilityProfile",
    "analyze_danceability",
]
