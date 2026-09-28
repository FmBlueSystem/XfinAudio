"""Read-only tonal interval profiling for audio tracks.

The analyzer folds a 12-bin chroma distribution into the 6-dimensional Tonal
Interval Vector (TIV) that underpins signal-level harmonic compatibility:
the 12 pitch classes are projected onto their six unique non-DC discrete
Fourier magnitudes, so each component measures energy at one interval-class
periodicity rather than one absolute key. This is the 6-dimensional
tonal-interval reduction introduced for tonal-centroid representations by
Harte & Sandler (2006), "Detecting Harmonic Change in Musical Audio" (Proc.
1st ACM Workshop on Audio and Music Computing Multimedia), and used as an
audio-derived harmonic-compatibility feature by Bibbo Frau & Faraldo (2022),
"A New Compatibility Measure for Harmonic EDM Mixing" (Springer LNCS,
DOI:10.1007/978-3-031-09917-5_37).

Like the spectral color profiler, this module is read-only: it never mutates
the source file, and a per-track profile is meant to be precomputed and cached
rather than recomputed on every scoring call.
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

CURRENT_TONAL_VERSION = 1
TIV_DIMENSIONS = 6

_ANALYSIS_SAMPLE_RATE = 22050
_HOP_LENGTH = 512
_ANALYSIS_WINDOW_SECONDS = 30.0
_PITCH_CLASSES = 12

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


class TonalProfile(BaseModel):
    """Normalized 6-dimensional Tonal Interval Vector for a single audio file."""

    model_config = ConfigDict(frozen=True)

    # Six non-DC DFT magnitudes of the mean pitch-class distribution. The vector
    # is scale-free for cosine comparison; only its direction carries meaning.
    tiv: tuple[float, float, float, float, float, float]
    # Confidence that the track is tonally focused: 1 - normalized pitch-class
    # entropy, so a single-pitch drone sits at 1.0 and a uniform distribution at
    # 0.0. Informational; it does not gate the compatibility score.
    tonal_coherence: float = Field(default=0.0, ge=0.0, le=1.0)
    analysis_version: int = Field(default=CURRENT_TONAL_VERSION, ge=1)


def tiv_compatibility(left: TonalProfile | None, right: TonalProfile | None) -> float | None:
    """Return the cosine similarity of two TIV vectors in [0, 1].

    Two tracks are harmonically compatible when their tonal-interval energy
    points in the same direction, so similarity is the cosine of the angle
    between the vectors. Returns ``None`` on degenerate input (a missing
    profile or an all-zero vector) so callers can score it as neutral rather
    than as a known clash. See Harte & Sandler (2006) for the tonal-interval
    representation and Bibbo Frau & Faraldo (2022) for its use as a
    harmonic-compatibility measure.
    """
    if left is None or right is None:
        return None
    left_vector = tuple(float(value) for value in left.tiv)
    right_vector = tuple(float(value) for value in right.tiv)
    left_norm = math.sqrt(sum(value * value for value in left_vector))
    right_norm = math.sqrt(sum(value * value for value in right_vector))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return None
    dot = sum(a * b for a, b in zip(left_vector, right_vector, strict=True))
    return float(max(0.0, min(1.0, dot / (left_norm * right_norm))))


def analyze_tonal_profile(path: Path | str) -> TonalProfile | None:
    """Return a tonal interval profile for ``path``.

    Returns ``None`` when the file cannot be read or the tonal dependency is
    unavailable. The source file is never modified.

    Analysis uses the canonical 30-second window centered at the track middle,
    matching the spectral profiler. Short tracks and files whose duration cannot
    be resolved are read from the beginning for up to 30 seconds.
    """
    try:
        import librosa
    except Exception:
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
            # Truncated files can declare a header duration longer than the real
            # stream; analyze what actually exists from the start instead.
            y, sr = librosa.load(
                audio_path,
                sr=_ANALYSIS_SAMPLE_RATE,
                mono=True,
                duration=_ANALYSIS_WINDOW_SECONDS,
            )
        return _profile_from_samples(y, sr, librosa)
    except Exception:
        return None


def _profile_from_samples(y: np.ndarray, sr: int | float, librosa: object) -> TonalProfile | None:
    """Build a tonal profile from decoded mono samples."""
    if y.size == 0:
        return None

    chroma = librosa.feature.chroma_cqt(  # type: ignore[attr-defined]
        y=y,
        sr=sr,
        hop_length=_HOP_LENGTH,
        norm=1,
    )
    if chroma.size == 0:
        return None
    mean_chroma = np.asarray(chroma, dtype=float).mean(axis=1)
    tiv = _chroma_to_tiv(mean_chroma)
    if sum(tiv) <= 0.0:
        # A tonally featureless window (silence, uniform noise) has no usable
        # interval vector; fail closed so scoring treats it as neutral.
        return None
    return TonalProfile(
        tiv=tiv,
        tonal_coherence=_tonal_coherence(mean_chroma),
        analysis_version=CURRENT_TONAL_VERSION,
    )


def _chroma_to_tiv(chroma: np.ndarray) -> tuple[float, float, float, float, float, float]:
    """Fold a 12-bin chroma vector into 6 Tonal Interval Vector magnitudes.

    The vector is L1-normalized to a pitch-class distribution, then its six
    unique non-DC discrete Fourier magnitudes are taken: ``|X_k|`` for
    ``k = 1..6``, where ``X_k = sum_n p_n * exp(-2*pi*i*k*n/12)``. A single
    pitch class maps to a flat all-ones vector; a uniform distribution maps to
    the zero vector. Returns six zeros for an all-zero input.
    """
    vector = np.asarray(chroma, dtype=float)
    if vector.ndim != 1 or vector.size != _PITCH_CLASSES:
        raise ValueError("chroma must be a 1-D vector of 12 pitch classes")
    total = float(vector.sum())
    if total <= 0.0:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    normalized = vector / total
    pitch_classes = np.arange(_PITCH_CLASSES)

    def magnitude(order: int) -> float:
        return float(abs((normalized * np.exp(-2j * math.pi * order * pitch_classes / _PITCH_CLASSES)).sum()))

    return (magnitude(1), magnitude(2), magnitude(3), magnitude(4), magnitude(5), magnitude(6))


def _tonal_coherence(chroma: np.ndarray) -> float:
    """Return tonal focus in [0, 1] as one minus normalized pitch-class entropy."""
    total = float(np.asarray(chroma, dtype=float).sum())
    if total <= 0.0:
        return 0.0
    probabilities = np.asarray(chroma, dtype=float) / total
    positive = probabilities[probabilities > 0.0]
    entropy = float(-(positive * np.log(positive)).sum())
    return float(max(0.0, min(1.0, 1.0 - entropy / math.log(_PITCH_CLASSES))))
