"""Application display boundary for spectral profile formatting."""

from __future__ import annotations

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.audio.spectral_profile import format_spectral_color as _format_spectral_color


def format_application_spectral_color(profile: SpectralProfile | None) -> str:
    """Return compact spectral color display text for UI adapters."""
    return _format_spectral_color(profile)


__all__ = ["format_application_spectral_color"]
