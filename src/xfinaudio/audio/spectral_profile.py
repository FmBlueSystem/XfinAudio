"""Read-only spectral color profiling for audio tracks.

The analyzer extracts a coarse color profile (RED/GREEN/BLUE) from the
mel-frequency energy distribution without mutating the source file.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ColorName = Literal["RED", "GREEN", "BLUE", "MIXED"]

_COLOR_BADGES: dict[ColorName, str] = {
    "RED": "🔴 RED",
    "GREEN": "🟢 GREEN",
    "BLUE": "🔵 BLUE",
    "MIXED": "⚪ MIXED",
}
_COLOR_EMOJI_ONLY: dict[ColorName, str] = {
    "RED": "🔴",
    "GREEN": "🟢",
    "BLUE": "🔵",
    "MIXED": "⚪",
}

_RED_MAX_HZ = 250.0
_GREEN_MAX_HZ = 2000.0
_ANALYSIS_SAMPLE_RATE = 22050
_N_MELS = 64
_N_FFT = 1024
_HOP_LENGTH = 512


class SpectralProfile(BaseModel):
    """Normalized spectral color fingerprint for a single audio file."""

    model_config = ConfigDict(frozen=True)

    red_ratio: float = Field(ge=0.0, le=1.0)
    green_ratio: float = Field(ge=0.0, le=1.0)
    blue_ratio: float = Field(ge=0.0, le=1.0)
    centroid_hz: float = Field(default=0.0, ge=0.0)
    rolloff_hz: float = Field(default=0.0, ge=0.0)
    rms: float = Field(default=0.0, ge=0.0)
    dominant_color: ColorName


def format_spectral_color(profile: SpectralProfile | None, *, emoji_only: bool = False) -> str:
    """Return a human-readable color badge for a spectral profile.

    Returns an empty string when no profile is available.
    """
    if profile is None:
        return ""
    lookup = _COLOR_EMOJI_ONLY if emoji_only else _COLOR_BADGES
    return lookup.get(profile.dominant_color, "")


def analyze_spectral_profile(path: Path | str) -> SpectralProfile | None:
    """Return a spectral color profile for ``path``.

    Returns ``None`` when the file cannot be read or the spectral dependency is
    unavailable. The source file is never modified.
    """
    try:
        import librosa
    except Exception:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            audio_path = Path(path)
            y, sr = librosa.load(audio_path, sr=_ANALYSIS_SAMPLE_RATE, mono=True)
            if y.size == 0:
                return None

            mel_spec = librosa.feature.melspectrogram(
                y=y,
                sr=sr,
                n_mels=_N_MELS,
                n_fft=_N_FFT,
                hop_length=_HOP_LENGTH,
            )
            mel_energies = mel_spec.sum(axis=1)
            mel_freqs = librosa.mel_frequencies(n_mels=_N_MELS, fmin=0.0, fmax=sr / 2.0)

            # Weight each band's energy by the square root of its center frequency to counteract
            # music's natural low-frequency energy concentration. Linear mel energy makes bass
            # dominate almost every track (measured 81% RED, 0% BLUE across the real library);
            # full-blown frequency weighting over-corrects to GREEN, while sqrt(f) balances RED/GREEN
            # discrimination on real audio and keeps BLUE reachable for genuinely bright tracks.
            weighted_energies = mel_energies * (mel_freqs**0.5)
            red_energy = weighted_energies[mel_freqs <= _RED_MAX_HZ].sum()
            green_energy = weighted_energies[(mel_freqs > _RED_MAX_HZ) & (mel_freqs <= _GREEN_MAX_HZ)].sum()
            blue_energy = weighted_energies[mel_freqs > _GREEN_MAX_HZ].sum()
            total_energy = red_energy + green_energy + blue_energy
            if total_energy <= 0:
                return None

            red_ratio = float(red_energy / total_energy)
            green_ratio = float(green_energy / total_energy)
            blue_ratio = float(blue_energy / total_energy)

            centroid = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=_N_FFT, hop_length=_HOP_LENGTH)
            rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, n_fft=_N_FFT, hop_length=_HOP_LENGTH)
            rms = librosa.feature.rms(y=y, frame_length=_N_FFT, hop_length=_HOP_LENGTH)

        return SpectralProfile(
            red_ratio=red_ratio,
            green_ratio=green_ratio,
            blue_ratio=blue_ratio,
            centroid_hz=float(centroid.mean()),
            rolloff_hz=float(rolloff.mean()),
            rms=float(rms.mean()),
            dominant_color=_dominant_color(red_ratio, green_ratio, blue_ratio),
        )
    except Exception:
        return None


_DOMINANT_COLOR_THRESHOLD = 0.45


def _dominant_color(red_ratio: float, green_ratio: float, blue_ratio: float) -> ColorName:
    """Classify the dominant color when one band holds a clear plurality.

    A color is dominant when its (frequency-weighted) ratio is at least 0.45; otherwise the
    profile is classified as MIXED. 0.45 is a clear plurality across three bands and, combined with
    the frequency-weighted energies, yields meaningful RED/GREEN/BLUE/MIXED discrimination instead
    of the previous bass-biased all-RED output.
    """
    ratios = {"RED": red_ratio, "GREEN": green_ratio, "BLUE": blue_ratio}
    dominant_name, dominant_value = max(ratios.items(), key=lambda item: item[1])
    if dominant_value >= _DOMINANT_COLOR_THRESHOLD:
        return dominant_name  # type: ignore[return-value]
    return "MIXED"


def score_spectral_similarity(left: SpectralProfile, right: SpectralProfile) -> float:
    """Return a similarity score in [0, 1] based on color vectors.

    The score uses cosine similarity over the (red, green, blue) energy ratios.
    Same-dominant-color tracks tend to score high; complementary-color tracks
    score low.
    """
    left_vector = (left.red_ratio, left.green_ratio, left.blue_ratio)
    right_vector = (right.red_ratio, right.green_ratio, right.blue_ratio)

    dot = sum(a * b for a, b in zip(left_vector, right_vector, strict=True))
    norm_left = sum(value * value for value in left_vector) ** 0.5
    norm_right = sum(value * value for value in right_vector) ** 0.5

    if norm_left <= 0 or norm_right <= 0:
        return 0.0

    similarity = dot / (norm_left * norm_right)
    return float(max(0.0, min(1.0, similarity)))
