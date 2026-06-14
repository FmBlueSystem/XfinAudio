"""Audio analysis utilities for XfinAudio."""

from __future__ import annotations

from xfinaudio.audio.batch_analyzer import analyze_paths
from xfinaudio.audio.spectral_profile import (
    SpectralProfile,
    analyze_spectral_profile,
    format_spectral_color,
    score_spectral_similarity,
)

__all__ = [
    "SpectralProfile",
    "analyze_paths",
    "analyze_spectral_profile",
    "format_spectral_color",
    "score_spectral_similarity",
]
