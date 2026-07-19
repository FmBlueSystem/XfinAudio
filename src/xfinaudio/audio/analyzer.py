"""Spectral analyzer boundary and default adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xfinaudio.audio.spectral_profile import SpectralProfile, analyze_spectral_profile


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


__all__ = ["LibrosaSpectralAnalyzer", "SpectralAnalyzer"]
