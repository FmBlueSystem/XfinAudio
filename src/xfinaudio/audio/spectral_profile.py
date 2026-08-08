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
CURRENT_EDGE_ANALYSIS_VERSION = 1

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
_EDGE_WINDOW_SECONDS = 30.0
_MIN_EDGE_TRACK_SECONDS = 65.0

# librosa emits these on every load that falls back from soundfile to audioread.
# Registered once, at import, rather than per call: warnings.catch_warnings()
# mutates process-global filter state, so with the analyzer running on 7-11
# threads one worker would blank every other thread's filters for the duration
# of its own analysis -- suppressing unrelated diagnostics, not just its own.
for _noisy_message in (
    r".*PySoundFile failed.*",
    r".*__audioread_load.*",
    r".*audioread.*[Dd]eprecated.*",
):
    warnings.filterwarnings("ignore", message=_noisy_message)


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


class EdgeSpectralProfile(BaseModel):
    """Spectral color fingerprints for the blendable edges of a track."""

    model_config = ConfigDict(frozen=True)

    intro: SpectralProfile
    outro: SpectralProfile
    analysis_version: int = CURRENT_EDGE_ANALYSIS_VERSION


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
        if y.size == 0 and offset > 0.0:
            # Truncated files can declare a header duration longer than the
            # real stream, so a mid-track seek lands past EOF and yields no
            # samples. Analyze what actually exists from the start instead.
            y, sr = librosa.load(
                audio_path,
                sr=_ANALYSIS_SAMPLE_RATE,
                mono=True,
                duration=_ANALYSIS_WINDOW_SECONDS,
            )
        return _profile_from_samples(y, sr, librosa)
    except Exception:
        return None


def _profile_from_samples(y: np.ndarray, sr: int | float, librosa: object) -> SpectralProfile | None:
    """Build a spectral profile from decoded mono samples."""
    if y.size == 0:
        return None

    # Compute the STFT once and share it across all four feature calls.
    stft = librosa.stft(y=y, n_fft=_N_FFT, hop_length=_HOP_LENGTH)  # type: ignore[attr-defined]
    magnitude = np.abs(stft)

    # Pass magnitude with power=1.0; classification depends only on ratios.
    mel_spec = librosa.feature.melspectrogram(  # type: ignore[attr-defined]
        S=magnitude,
        sr=sr,
        n_mels=_N_MELS,
        n_fft=_N_FFT,
        hop_length=_HOP_LENGTH,
        power=1.0,
    )
    mel_energies = mel_spec.sum(axis=1)
    mel_freqs = librosa.mel_frequencies(n_mels=_N_MELS, fmin=0.0, fmax=sr / 2.0)  # type: ignore[attr-defined]

    red_energy = mel_energies[mel_freqs <= _RED_MAX_HZ].sum()
    green_energy = mel_energies[(mel_freqs > _RED_MAX_HZ) & (mel_freqs <= _GREEN_MAX_HZ)].sum()
    blue_energy = mel_energies[mel_freqs > _GREEN_MAX_HZ].sum()
    total_energy = red_energy + green_energy + blue_energy
    if total_energy <= 0:
        return None

    red_ratio = float(red_energy / total_energy)
    green_ratio = float(green_energy / total_energy)
    blue_ratio = float(blue_energy / total_energy)

    centroid = librosa.feature.spectral_centroid(  # type: ignore[attr-defined]
        S=magnitude, sr=sr, n_fft=_N_FFT, hop_length=_HOP_LENGTH
    )
    rolloff = librosa.feature.spectral_rolloff(  # type: ignore[attr-defined]
        S=magnitude, sr=sr, n_fft=_N_FFT, hop_length=_HOP_LENGTH, roll_percent=0.85
    )
    rms = librosa.feature.rms(  # type: ignore[attr-defined]
        S=magnitude, frame_length=_N_FFT, hop_length=_HOP_LENGTH
    )

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


def analyze_edge_spectral_profile(path: Path | str) -> EdgeSpectralProfile | None:
    """Return fixed-window intro and outro spectral profiles for ``path``."""
    try:
        import librosa
    except Exception:
        return None

    try:
        audio_path = Path(path)
        duration = float(librosa.get_duration(path=audio_path))
        if duration < _MIN_EDGE_TRACK_SECONDS:
            return None
        # Fixed windows avoid another tag read; persisted cue points are the
        # upgrade path when precise musical boundaries become available.
        intro_samples, intro_sr = librosa.load(
            audio_path,
            sr=_ANALYSIS_SAMPLE_RATE,
            mono=True,
            offset=0.0,
            duration=_EDGE_WINDOW_SECONDS,
        )
        outro_samples, outro_sr = librosa.load(
            audio_path,
            sr=_ANALYSIS_SAMPLE_RATE,
            mono=True,
            offset=duration - _EDGE_WINDOW_SECONDS,
            duration=_EDGE_WINDOW_SECONDS,
        )
        intro = _profile_from_samples(intro_samples, intro_sr, librosa)
        outro = _profile_from_samples(outro_samples, outro_sr, librosa)
        if intro is None or outro is None:
            return None
        return EdgeSpectralProfile(intro=intro, outro=outro)
    except Exception:
        return None


def _dominant_color(red_ratio: float, green_ratio: float, blue_ratio: float) -> ColorName:
    """Classify color by per-band thresholds and threshold excess.

    When multiple bands qualify, the largest excess wins. Dictionary order
    provides the deterministic RED, GREEN, BLUE priority for exact ties.
    Thresholds are calibrated against the mid-track-window distribution of a
    real 10,386-profile library (GREEN needs a higher bar because mid-track
    energy concentrates in the mids; BLUE a lower one).
    """
    candidates: dict[ColorName, float] = {
        "RED": red_ratio - 0.45,
        "GREEN": green_ratio - 0.48,
        "BLUE": blue_ratio - 0.22,
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
