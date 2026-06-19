"""Pure transition helpers for desktop AppState updates."""

from __future__ import annotations

from typing import Protocol

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.desktop.app_state import AppState
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class CompletedRecommendationResult(Protocol):
    """Result-like object returned by recommendation workflow completion."""

    recommendation: PlaylistRecommendation
    explanation: PlaylistExplanation
    quality_report: RecommendationQualityReport


def apply_spectral_profile(state: AppState, *, path: str, profile: SpectralProfile) -> AppState:
    """Return a new state with a spectral profile applied to matching track records."""
    scanned_records = list(state.scanned_records)
    records_by_path = dict(state.records_by_path)

    for index, record in enumerate(scanned_records):
        if record.path == path:
            scanned_records[index] = record.model_copy(update={"spectral_profile": profile})
            break

    if path in records_by_path:
        records_by_path[path] = records_by_path[path].model_copy(update={"spectral_profile": profile})

    return state.model_copy(
        update={
            "scanned_records": scanned_records,
            "records_by_path": records_by_path,
        }
    )


def apply_recommendation_completion(state: AppState, result: CompletedRecommendationResult) -> AppState:
    """Return a new state with completed recommendation fields applied."""
    return state.model_copy(
        update={
            "last_recommendation": result.recommendation,
            "last_playlist_explanation": result.explanation,
            "last_quality_report": result.quality_report,
            "playlist_removed_paths": frozenset(),
            "applied_variant_name": None,
        }
    )


__all__ = [
    "CompletedRecommendationResult",
    "apply_recommendation_completion",
    "apply_spectral_profile",
]
