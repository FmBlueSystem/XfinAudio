"""Application workflow service for scan, recommendation, explanation, and quality sequencing."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeGuard

from pydantic import BaseModel, ConfigDict

from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.library import ports as library_ports
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.ports import TrackRepositoryPort
from xfinaudio.library.scan_service import (
    ProfileCache,
    ProgressCallback,
    ScanCancellationToken,
    ScanCancelledError,
    ScanProgress,
)
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport, build_quality_report
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.loudness_policy import DEFAULT_LOUDNESS_BAND, LoudnessBand
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
from xfinaudio.recommendation.strategies import StrategyName

# A 10,000-file scan runs for a long time before its completion save, so
# records are upserted in bounded batches while it runs: ~200 records or ~5
# seconds, whichever comes first. Pruning stays in the completion save.
SCAN_FLUSH_BATCH_SIZE = 200
SCAN_FLUSH_INTERVAL_SECONDS = 5.0


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
    persisted_record_count: int = 0
    """Records already written by incremental flushes during the scan."""


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
        flush_batch_size: int = SCAN_FLUSH_BATCH_SIZE,
        flush_interval_seconds: float = SCAN_FLUSH_INTERVAL_SECONDS,
    ) -> ScanWorkflowResult:
        """Scan a folder, persist records incrementally, and return display-ready counts.

        Records are upserted in batches while the scan runs so a crash or a
        window close mid-scan keeps the tracks that were already read. Those
        batches never prune: ``pruned_root`` is passed once, in the completion
        save, so no incremental write can delete rows for files not yet scanned.
        """
        cache_loader: Callable[[list[Path]], ProfileCache] | None = None
        if _supports_spectral_profile_cache(self.repository):
            repo = self.repository

            def _load_cache(paths: list[Path]) -> ProfileCache:
                return repo.load_spectral_profile_cache([str(path) for path in paths])

            cache_loader = _load_cache

        pending_records: list[TrackRecord] = []
        persisted_record_count = 0
        last_flush = time.monotonic()

        def _flush_pending() -> None:
            # Only ever called right after a record was buffered.
            nonlocal persisted_record_count, last_flush
            self.repository.save_scan_results(list(pending_records))
            persisted_record_count += len(pending_records)
            pending_records.clear()
            last_flush = time.monotonic()

        def _buffer_progress(progress: ScanProgress) -> None:
            if progress.record is not None:
                pending_records.append(progress.record)
                if len(pending_records) >= flush_batch_size or time.monotonic() - last_flush >= flush_interval_seconds:
                    _flush_pending()
            if on_progress is not None:
                on_progress(progress)

        try:
            records = self.scan_service.scan(
                folder,
                on_progress=_buffer_progress,
                cancellation_token=cancellation_token,
                parallel_spectral_analysis=True,
                profile_cache_loader=cache_loader,
                resolve_spectral_profiles=resolve_spectral_profiles,
            )
        except ScanCancelledError as exc:
            # An explicit cancel keeps whatever batches already reached disk and
            # never prunes; the unflushed tail is dropped with the scan.
            return ScanWorkflowResult(
                records=exc.records,
                complete_count=0,
                incomplete_count=0,
                cancelled=True,
                persisted_record_count=persisted_record_count,
            )

        self.repository.save_scan_results(records, pruned_root=folder)
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
            persisted_record_count=persisted_record_count,
        )

    def recommend(
        self,
        records: list[TrackRecord],
        strategy_name: StrategyName | str,
        controls: DJControls | None = None,
        spectral_cohesion: float = 0.0,
        target_count: int | None = None,
        target_duration_minutes: float | None = None,
        played_seconds_per_track: float | None = None,
        color_anchor_path: str | None = None,
        loudness_band: LoudnessBand = DEFAULT_LOUDNESS_BAND,
    ) -> RecommendationWorkflowResult:
        """Build a recommendation plus explanation and quality report for UI rendering.

        ``target_duration_minutes`` is the DJ's slot length, which is how the job
        is actually booked; ``target_count`` is the lower-level equivalent. Both
        are separate from how many candidates ``records`` offers the optimizer.
        """
        recommendation = recommend_playlist(
            records,
            strategy_name,
            controls=controls,
            spectral_cohesion=spectral_cohesion,
            target_count=target_count,
            target_duration_minutes=target_duration_minutes,
            played_seconds_per_track=played_seconds_per_track,
            color_anchor_path=color_anchor_path,
            loudness_band=loudness_band,
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
