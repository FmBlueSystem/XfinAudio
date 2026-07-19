"""Read-only spectral color profiling for audio tracks.

The analyzer extracts a coarse color profile (RED/GREEN/BLUE) from the
mel-frequency energy distribution without mutating the source file.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

ColorName = Literal["RED", "GREEN", "BLUE", "MIXED"]
CURRENT_ANALYSIS_VERSION = 2

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
_ANALYSIS_WINDOW_SECONDS = 30.0


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
    analysis_version: int = Field(default=1, ge=1)


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

    Analysis uses the canonical 30-second window centered at the track middle.
    Short tracks and files whose duration cannot be resolved are read from the
    beginning for up to 30 seconds.
    """
    try:
        import librosa
    except Exception:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
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
                sr=_ANALYSIS_SAMPLE_RATE,
                mono=True,
                offset=offset,
                duration=_ANALYSIS_WINDOW_SECONDS,
            )
            if y.size == 0:
                return None

            # Compute the STFT once and share it across all four feature
            # calls. Without sharing, librosa would run the same FFT three
            # extra times internally (once each for melspectrogram,
            # spectral_centroid, and spectral_rolloff), which is the dominant
            # cost of the analyzer on a real DJ library.
            stft = librosa.stft(y=y, n_fft=_N_FFT, hop_length=_HOP_LENGTH)
            magnitude = np.abs(stft)

            # melspectrogram defaults to power=2.0 (expects |STFT|²). Pass
            # the magnitude directly with power=1.0 to skip squaring; color
            # classification only depends on the ratio of band energies,
            # which is scale-invariant.
            mel_spec = librosa.feature.melspectrogram(
                S=magnitude,
                sr=sr,
                n_mels=_N_MELS,
                n_fft=_N_FFT,
                hop_length=_HOP_LENGTH,
                power=1.0,
            )
            mel_energies = mel_spec.sum(axis=1)
            mel_freqs = librosa.mel_frequencies(n_mels=_N_MELS, fmin=0.0, fmax=sr / 2.0)

            red_energy = mel_energies[mel_freqs <= _RED_MAX_HZ].sum()
            green_energy = mel_energies[(mel_freqs > _RED_MAX_HZ) & (mel_freqs <= _GREEN_MAX_HZ)].sum()
            blue_energy = mel_energies[mel_freqs > _GREEN_MAX_HZ].sum()
            total_energy = red_energy + green_energy + blue_energy
            if total_energy <= 0:
                return None

            red_ratio = float(red_energy / total_energy)
            green_ratio = float(green_energy / total_energy)
            blue_ratio = float(blue_energy / total_energy)

            centroid = librosa.feature.spectral_centroid(S=magnitude, sr=sr, n_fft=_N_FFT, hop_length=_HOP_LENGTH)
            rolloff = librosa.feature.spectral_rolloff(
                S=magnitude, sr=sr, n_fft=_N_FFT, hop_length=_HOP_LENGTH, roll_percent=0.85
            )
            rms = librosa.feature.rms(S=magnitude, frame_length=_N_FFT, hop_length=_HOP_LENGTH)

        return SpectralProfile(
            red_ratio=red_ratio,
            green_ratio=green_ratio,
            blue_ratio=blue_ratio,
            centroid_hz=float(centroid.mean()),
            rolloff_hz=float(rolloff.mean()),
            rms=float(rms.mean()),
            dominant_color=_dominant_color(red_ratio, green_ratio, blue_ratio),
            analysis_version=CURRENT_ANALYSIS_VERSION,
        )
    except Exception:
        return None


def _dominant_color(red_ratio: float, green_ratio: float, blue_ratio: float) -> ColorName:
    """Classify color by per-band thresholds and threshold excess.

    When multiple bands qualify, the largest excess wins. Dictionary order
    provides the deterministic RED, GREEN, BLUE priority for exact ties.
    """
    candidates: dict[ColorName, float] = {
        "RED": red_ratio - 0.45,
        "GREEN": green_ratio - 0.45,
        "BLUE": blue_ratio - 0.25,
    }
    eligible: dict[ColorName, float] = {color: excess for color, excess in candidates.items() if excess >= 0.0}
    if not eligible:
        return "MIXED"
    return max(eligible.items(), key=lambda item: item[1])[0]


def dominant_color_for_ratios(red_ratio: float, green_ratio: float, blue_ratio: float) -> ColorName:
    """Return the spectral color classification for normalized band ratios."""
    return _dominant_color(red_ratio, green_ratio, blue_ratio)


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
