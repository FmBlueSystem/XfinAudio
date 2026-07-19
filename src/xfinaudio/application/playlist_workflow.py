"""Application workflow service for scan, recommendation, explanation, and quality sequencing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeGuard

from pydantic import BaseModel, ConfigDict

from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.library import ports as library_ports
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.ports import TrackRepositoryPort
from xfinaudio.library.scan_service import ProfileCache, ProgressCallback, ScanCancellationToken, ScanCancelledError
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport, build_quality_report
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
from xfinaudio.recommendation.strategies import StrategyName


class ScanService(Protocol):
    """Protocol for metadata scanning services used by application workflows."""

    def scan(
        self,
        folder: Path,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation_token: ScanCancellationToken | None = None,
        parallel_spectral_analysis: bool = True,
        spectral_max_workers: int | None = None,
        previous_profile_cache: ProfileCache | None = None,
        profile_cache_loader: Callable[[list[Path]], ProfileCache] | None = None,
        resolve_spectral_profiles: bool = True,
    ) -> list[TrackRecord]:
        """Scan folder and return track records."""
        ...


class ScanWorkflowResult(BaseModel):
    """Result returned after scanning and persistence complete."""

    model_config = ConfigDict(frozen=True)

    records: list[TrackRecord]
    complete_count: int
    incomplete_count: int
    cancelled: bool = False


class RecommendationWorkflowResult(BaseModel):
    """Result returned after recommendation, explanation, and quality reporting complete."""

    model_config = ConfigDict(frozen=True)

    recommendation: PlaylistRecommendation
    explanation: PlaylistExplanation
    quality_report: RecommendationQualityReport


class PlaylistWorkflowService:
    """Application service that sequences library scan and playlist recommendation workflows."""

    def __init__(self, *, scan_service: ScanService, repository: TrackRepositoryPort) -> None:
        self.scan_service = scan_service
        self.repository = repository

    def scan_folder(
        self,
        folder: Path,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation_token: ScanCancellationToken | None = None,
        resolve_spectral_profiles: bool = True,
    ) -> ScanWorkflowResult:
        """Scan a folder, persist complete scan records, and return display-ready counts."""
        cache_loader: Callable[[list[Path]], ProfileCache] | None = None
        if _supports_spectral_profile_cache(self.repository):
            repo = self.repository

            def _load_cache(paths: list[Path]) -> ProfileCache:
                return repo.load_spectral_profile_cache([str(path) for path in paths])

            cache_loader = _load_cache

        try:
            records = self.scan_service.scan(
                folder,
                on_progress=on_progress,
                cancellation_token=cancellation_token,
                parallel_spectral_analysis=True,
                profile_cache_loader=cache_loader,
                resolve_spectral_profiles=resolve_spectral_profiles,
            )
        except ScanCancelledError as exc:
            return ScanWorkflowResult(
                records=exc.records,
                complete_count=0,
                incomplete_count=0,
                cancelled=True,
            )

        self.repository.save_scan_results(records)
        if _supports_stored_track_read(self.repository):
            stored_profiles = {
                record.path: record.spectral_profile
                for record in self.repository.list_display_tracks()
                if record.spectral_profile is not None
            }
            records = [
                record.model_copy(update={"spectral_profile": stored_profiles[record.path]})
                if record.spectral_profile is None and record.path in stored_profiles
                else record
                for record in records
            ]
        complete_count = sum(1 for record in records if record.metadata_status == "complete")
        return ScanWorkflowResult(
            records=records,
            complete_count=complete_count,
            incomplete_count=len(records) - complete_count,
        )

    def recommend(
        self,
        records: list[TrackRecord],
        strategy_name: StrategyName | str,
        controls: DJControls | None = None,
        spectral_cohesion: float = 0.0,
    ) -> RecommendationWorkflowResult:
        """Build a recommendation plus explanation and quality report for UI rendering."""
        recommendation = recommend_playlist(
            records, strategy_name, controls=controls, spectral_cohesion=spectral_cohesion
        )
        explanation = build_playlist_explanation(recommendation)
        quality_report = build_quality_report(recommendation)
        return RecommendationWorkflowResult(
            recommendation=recommendation,
            explanation=explanation,
            quality_report=quality_report,
        )


def _supports_spectral_profile_cache(
    repository: TrackRepositoryPort,
) -> TypeGuard[library_ports.TrackSpectralProfileCacheReaderPort]:
    return hasattr(repository, "load_spectral_profile_cache")


def _supports_stored_track_read(repository: object) -> TypeGuard[library_ports.TrackDisplayRepositoryPort]:
    return hasattr(repository, "list_display_tracks")


__all__ = [
    "PlaylistWorkflowService",
    "RecommendationWorkflowResult",
    "ScanService",
    "ScanWorkflowResult",
]
