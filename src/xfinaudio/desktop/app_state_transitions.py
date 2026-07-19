"""Pure transition helpers for desktop AppState updates."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.desktop.app_state import AppState
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan


class CompletedRecommendationResult(Protocol):
    """Result-like object returned by recommendation workflow completion."""

    recommendation: PlaylistRecommendation
    explanation: PlaylistExplanation
    quality_report: RecommendationQualityReport


@dataclass(frozen=True)
class PrepCopilotVariantApplication:
    """State payload for an applied Prep Copilot variant."""

    recommendation: PlaylistRecommendation
    explanation: PlaylistExplanation
    quality_report: RecommendationQualityReport
    readiness_report: DjReadinessReport
    variant_name: str


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


def apply_scan_context_reset(state: AppState) -> AppState:
    """Return a new state with scan-dependent recommendation context cleared."""
    return state.model_copy(
        update={
            "scanned_records": [],
            "records_by_path": {},
            "last_recommendation": None,
            "last_playlist_explanation": None,
            "last_quality_report": None,
            "last_dj_readiness_report": None,
            "last_prep_copilot_plan": None,
            "applied_variant_name": None,
            "playlist_removed_paths": frozenset(),
        }
    )


def apply_library_folder_selected(state: AppState, folder: Path) -> AppState:
    """Return a new state for a selected library folder with scan context cleared."""
    return apply_scan_context_reset(state).model_copy(update={"selected_folder": folder})


def apply_library_records_loaded(state: AppState, records: Iterable[TrackRecord]) -> AppState:
    """Return a new state with loaded library records and lookup map applied."""
    scanned_records = list(records)
    return state.model_copy(
        update={
            "scanned_records": scanned_records,
            "records_by_path": {record.path: record for record in scanned_records},
        }
    )


def apply_playlist_track_removed(state: AppState, path: str) -> AppState:
    """Return a new state with a playlist track marked as removed."""
    return state.model_copy(update={"playlist_removed_paths": state.playlist_removed_paths | {path}})


def apply_playlist_track_replaced(state: AppState, *, path: str, recommendation: PlaylistRecommendation) -> AppState:
    """Return a new state with a removed track marked and its backfilled recommendation applied."""
    return state.model_copy(
        update={
            "last_recommendation": recommendation,
            "playlist_removed_paths": state.playlist_removed_paths | {path},
        }
    )


def apply_playlist_track_restored(
    state: AppState, path: str, recommendation: PlaylistRecommendation | None = None
) -> AppState:
    """Return a new state with a playlist track restored.

    When ``recommendation`` is provided, the pre-removal recommendation is
    restored too (undo of a backfilled removal).
    """
    update: dict[str, object] = {"playlist_removed_paths": state.playlist_removed_paths - {path}}
    if recommendation is not None:
        update["last_recommendation"] = recommendation
    return state.model_copy(update=update)


def apply_prep_copilot_variant(state: AppState, payload: PrepCopilotVariantApplication) -> AppState:
    """Return a new state with an applied Prep Copilot variant result."""
    return state.model_copy(
        update={
            "last_recommendation": payload.recommendation,
            "last_playlist_explanation": payload.explanation,
            "last_quality_report": payload.quality_report,
            "last_dj_readiness_report": payload.readiness_report,
            "playlist_removed_paths": frozenset(),
            "applied_variant_name": payload.variant_name,
        }
    )


def apply_tracks_excluded(state: AppState, paths: Iterable[str]) -> AppState:
    """Return a new state with selected tracks excluded."""
    return state.model_copy(update={"excluded_paths": state.excluded_paths | frozenset(paths)})


def apply_tracks_locked(state: AppState, paths: Iterable[str]) -> AppState:
    """Return a new state with selected tracks locked."""
    return state.model_copy(update={"locked_paths": state.locked_paths | frozenset(paths)})


def apply_track_constraints_cleared(state: AppState) -> AppState:
    """Return a new state with excluded and locked track constraints cleared."""
    return state.model_copy(update={"excluded_paths": frozenset(), "locked_paths": frozenset()})


def apply_prep_copilot_plan_generated(state: AppState, plan: PrepCopilotPlan) -> AppState:
    """Return a new state with a generated Prep Copilot plan stored."""
    return state.model_copy(update={"last_prep_copilot_plan": plan})


def apply_prep_copilot_plan_cleared(state: AppState) -> AppState:
    """Return a new state with the Prep Copilot plan cleared."""
    return state.model_copy(update={"last_prep_copilot_plan": None})


def apply_saved_playlist_export_recommendation(state: AppState, recommendation: PlaylistRecommendation) -> AppState:
    """Return a new state with a saved-playlist export recommendation applied."""
    return state.model_copy(update={"last_recommendation": recommendation})


__all__ = [
    "CompletedRecommendationResult",
    "PrepCopilotVariantApplication",
    "apply_playlist_track_removed",
    "apply_playlist_track_replaced",
    "apply_playlist_track_restored",
    "apply_prep_copilot_plan_cleared",
    "apply_prep_copilot_plan_generated",
    "apply_prep_copilot_variant",
    "apply_recommendation_completion",
    "apply_saved_playlist_export_recommendation",
    "apply_track_constraints_cleared",
    "apply_tracks_excluded",
    "apply_tracks_locked",
    "apply_library_folder_selected",
    "apply_library_records_loaded",
    "apply_scan_context_reset",
    "apply_spectral_profile",
]
