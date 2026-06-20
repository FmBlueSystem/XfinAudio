"""Application facade for the vertical playlist recommendation/save flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xfinaudio.application.saved_playlists import SavedPlaylistExport
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist
from xfinaudio.library.scan_service import ProgressCallback, ScanCancellationToken
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import StrategyName


class ScanWorkflowResultLike(Protocol):
    """Scan workflow result shape required by the vertical facade."""

    @property
    def records(self) -> list[TrackRecord]:
        """Return scanned records."""
        ...


class RecommendationWorkflowResultLike(Protocol):
    """Recommendation workflow result shape required by the vertical facade."""

    @property
    def recommendation(self) -> PlaylistRecommendation:
        """Return the built recommendation."""
        ...


class PlaylistWorkflowRecommender(Protocol):
    """Application dependency that can build a playlist recommendation."""

    def recommend(
        self,
        records: list[TrackRecord],
        strategy_name: StrategyName | str,
        controls: DJControls | None = None,
        spectral_cohesion: float = 0.0,
    ) -> RecommendationWorkflowResultLike:
        """Return a recommendation workflow result."""
        ...


class PlaylistWorkflowScanner(Protocol):
    """Application dependency that can scan a music folder."""

    def scan_folder(
        self,
        folder: Path,
        *,
        on_progress: ProgressCallback | None = None,
        cancellation_token: ScanCancellationToken | None = None,
        resolve_spectral_profiles: bool = True,
    ) -> ScanWorkflowResultLike:
        """Scan a folder and return scanned records."""
        ...


class PlaylistWorkflow(PlaylistWorkflowScanner, PlaylistWorkflowRecommender, Protocol):
    """Application dependency that can scan and recommend."""


class RecommendationSaver(Protocol):
    """Application dependency that can persist a recommendation as a playlist."""

    def save_recommendation(
        self,
        recommendation: PlaylistRecommendation,
        *,
        name: str | None = None,
    ) -> Playlist:
        """Persist the recommendation and return the saved playlist."""
        ...


class SavedPlaylistExportBuilder(Protocol):
    """Application dependency that can build an exportable saved playlist recommendation."""

    def build_export_recommendation(
        self,
        playlist_id: int,
        scanned_records: list[TrackRecord],
    ) -> SavedPlaylistExport | None:
        """Return an exportable recommendation for a saved playlist."""
        ...


class SavedPlaylistStore(RecommendationSaver, SavedPlaylistExportBuilder, Protocol):
    """Application dependency that can save and prepare saved playlists for export."""


class SavedPlaylistApplicationExporter(Protocol):
    """Application dependency that exports a saved playlist recommendation."""

    def export_saved_playlist(
        self,
        *,
        recommendation: PlaylistRecommendation,
        requested_name: str,
    ) -> object:
        """Export a saved playlist recommendation using the requested export name."""
        ...


@dataclass(frozen=True)
class VerticalPlaylistFlowResult:
    """Application result for recommending and saving a playlist."""

    recommendation_result: RecommendationWorkflowResultLike
    playlist: Playlist

    @property
    def recommendation(self) -> PlaylistRecommendation:
        """Return the recommendation saved by this vertical flow."""
        return self.recommendation_result.recommendation


@dataclass(frozen=True)
class VerticalScanRecommendationResult:
    """Application result for scanning and recommending a playlist."""

    scan_result: ScanWorkflowResultLike
    recommendation_result: RecommendationWorkflowResultLike

    @property
    def recommendation(self) -> PlaylistRecommendation:
        """Return the recommendation built from scanned records."""
        return self.recommendation_result.recommendation


@dataclass(frozen=True)
class VerticalSavedPlaylistExportResult:
    """Application result for exporting a saved playlist."""

    saved_playlist_export: SavedPlaylistExport
    export_result: object

    @property
    def playlist(self) -> Playlist:
        """Return the saved playlist used as the export source."""
        return self.saved_playlist_export.playlist

    @property
    def recommendation(self) -> PlaylistRecommendation:
        """Return the recommendation exported by this vertical flow."""
        return self.saved_playlist_export.recommendation


class VerticalPlaylistFlow:
    """Compose existing application services into a vertical recommend/save flow."""

    def __init__(
        self,
        *,
        playlist_workflow: PlaylistWorkflow,
        saved_playlists: SavedPlaylistStore,
        saved_playlist_exporter: SavedPlaylistApplicationExporter | None = None,
    ) -> None:
        self._playlist_workflow = playlist_workflow
        self._saved_playlists = saved_playlists
        self._saved_playlist_exporter = saved_playlist_exporter

    def scan_and_recommend(
        self,
        folder: Path,
        strategy_name: StrategyName | str,
        *,
        controls: DJControls | None = None,
        spectral_cohesion: float = 0.0,
        on_progress: ProgressCallback | None = None,
        cancellation_token: ScanCancellationToken | None = None,
        resolve_spectral_profiles: bool = True,
    ) -> VerticalScanRecommendationResult:
        """Scan a folder, then recommend from the scanned records."""
        scan_result = self._playlist_workflow.scan_folder(
            folder,
            on_progress=on_progress,
            cancellation_token=cancellation_token,
            resolve_spectral_profiles=resolve_spectral_profiles,
        )
        recommendation_result = self._playlist_workflow.recommend(
            scan_result.records,
            strategy_name,
            controls=controls,
            spectral_cohesion=spectral_cohesion,
        )
        return VerticalScanRecommendationResult(
            scan_result=scan_result,
            recommendation_result=recommendation_result,
        )

    def recommend_and_save(
        self,
        records: list[TrackRecord],
        strategy_name: StrategyName | str,
        *,
        controls: DJControls | None = None,
        spectral_cohesion: float = 0.0,
        playlist_name: str | None = None,
    ) -> VerticalPlaylistFlowResult:
        """Recommend from records and persist the recommendation as a saved playlist."""
        recommendation_result = self._playlist_workflow.recommend(
            records,
            strategy_name,
            controls=controls,
            spectral_cohesion=spectral_cohesion,
        )
        playlist = self._saved_playlists.save_recommendation(
            recommendation_result.recommendation,
            name=playlist_name,
        )
        return VerticalPlaylistFlowResult(
            recommendation_result=recommendation_result,
            playlist=playlist,
        )

    def export_saved_playlist(
        self,
        *,
        playlist_id: int,
        scanned_records: list[TrackRecord],
    ) -> VerticalSavedPlaylistExportResult | None:
        """Export a saved playlist through the injected application exporter."""
        if self._saved_playlist_exporter is None:
            raise ValueError("saved_playlist_exporter is required to export a saved playlist")
        saved_playlist_export = self._saved_playlists.build_export_recommendation(
            playlist_id,
            scanned_records,
        )
        if saved_playlist_export is None:
            return None
        export_result = self._saved_playlist_exporter.export_saved_playlist(
            recommendation=saved_playlist_export.recommendation,
            requested_name=saved_playlist_export.playlist.name,
        )
        return VerticalSavedPlaylistExportResult(
            saved_playlist_export=saved_playlist_export,
            export_result=export_result,
        )


__all__ = [
    "PlaylistWorkflow",
    "PlaylistWorkflowRecommender",
    "PlaylistWorkflowScanner",
    "RecommendationSaver",
    "RecommendationWorkflowResultLike",
    "ScanWorkflowResultLike",
    "SavedPlaylistApplicationExporter",
    "SavedPlaylistExportBuilder",
    "SavedPlaylistStore",
    "VerticalPlaylistFlow",
    "VerticalPlaylistFlowResult",
    "VerticalSavedPlaylistExportResult",
    "VerticalScanRecommendationResult",
]
