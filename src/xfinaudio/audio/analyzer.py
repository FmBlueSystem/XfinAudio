"""Read-only audio analyzer boundaries and default adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xfinaudio.audio.danceability import DanceabilityProfile, analyze_danceability
from xfinaudio.audio.spectral_profile import (
    EdgeSpectralProfile,
    SpectralProfile,
    analyze_edge_spectral_profile,
    analyze_spectral_profile,
)
from xfinaudio.audio.tonal_profile import TonalProfile, analyze_tonal_profile


class SpectralAnalyzer(Protocol):
    """Contract for read-only spectral profile analysis."""

    def analyze(self, path: Path) -> SpectralProfile | None:
        """Return a spectral profile for a path without mutating the source file."""
        ...


@dataclass(frozen=True)
class LibrosaSpectralAnalyzer:
    """Default adapter for the existing librosa-backed analyzer."""

    def analyze(self, path: Path) -> SpectralProfile | None:
        return analyze_spectral_profile(path)


class DanceabilityAnalyzer(Protocol):
    """Contract for read-only danceability profile analysis."""

    def analyze(self, path: Path) -> DanceabilityProfile | None:
        """Return a danceability profile without mutating the source file."""
        ...


@dataclass(frozen=True)
class LibrosaDanceabilityAnalyzer:
    """Default adapter for the existing librosa-backed danceability analyzer."""

    def analyze(self, path: Path) -> DanceabilityProfile | None:
        return analyze_danceability(path)


class EdgeSpectralAnalyzer(Protocol):
    """Contract for read-only intro/outro spectral analysis."""

    def analyze(self, path: Path) -> EdgeSpectralProfile | None:
        """Return edge profiles without mutating the source file."""
        ...


@dataclass(frozen=True)
class LibrosaEdgeSpectralAnalyzer:
    """Default adapter for the librosa-backed edge analyzer."""

    def analyze(self, path: Path) -> EdgeSpectralProfile | None:
        return analyze_edge_spectral_profile(path)


class TonalAnalyzer(Protocol):
    """Contract for read-only tonal interval profile analysis."""

    def analyze(self, path: Path) -> TonalProfile | None:
        """Return a tonal profile for a path without mutating the source file."""
        ...


@dataclass(frozen=True)
class LibrosaTonalAnalyzer:
    """Default adapter for the librosa-backed tonal interval analyzer."""

    def analyze(self, path: Path) -> TonalProfile | None:
        return analyze_tonal_profile(path)


__all__ = [
    "DanceabilityAnalyzer",
    "EdgeSpectralAnalyzer",
    "LibrosaDanceabilityAnalyzer",
    "LibrosaEdgeSpectralAnalyzer",
    "LibrosaSpectralAnalyzer",
    "LibrosaTonalAnalyzer",
    "SpectralAnalyzer",
    "TonalAnalyzer",
]
