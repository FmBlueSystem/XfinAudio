"""Audio analysis utilities for XfinAudio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xfinaudio.audio.analysis_planning import AnalysisPlan, plan_analysis_paths
    from xfinaudio.audio.batch_analyzer import analyze_paths
    from xfinaudio.audio.spectral_profile import (
        SpectralProfile,
        analyze_spectral_profile,
        format_spectral_color,
        score_spectral_similarity,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "AnalysisPlan": ("xfinaudio.audio.analysis_planning", "AnalysisPlan"),
    "SpectralProfile": ("xfinaudio.audio.spectral_profile", "SpectralProfile"),
    "analyze_paths": ("xfinaudio.audio.batch_analyzer", "analyze_paths"),
    "analyze_spectral_profile": ("xfinaudio.audio.spectral_profile", "analyze_spectral_profile"),
    "format_spectral_color": ("xfinaudio.audio.spectral_profile", "format_spectral_color"),
    "plan_analysis_paths": ("xfinaudio.audio.analysis_planning", "plan_analysis_paths"),
    "score_spectral_similarity": ("xfinaudio.audio.spectral_profile", "score_spectral_similarity"),
}

__all__ = [
    "AnalysisPlan",
    "SpectralProfile",
    "analyze_paths",
    "analyze_spectral_profile",
    "format_spectral_color",
    "plan_analysis_paths",
    "score_spectral_similarity",
]


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily to keep pure audio planning imports isolated."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
