"""Application facade for the vertical playlist recommendation/save flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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


class VerticalPlaylistFlow:
    """Compose existing application services into a vertical recommend/save flow."""

    def __init__(
        self,
        *,
        playlist_workflow: PlaylistWorkflow,
        saved_playlists: RecommendationSaver,
    ) -> None:
        self._playlist_workflow = playlist_workflow
        self._saved_playlists = saved_playlists

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


__all__ = [
    "PlaylistWorkflow",
    "PlaylistWorkflowRecommender",
    "PlaylistWorkflowScanner",
    "RecommendationSaver",
    "RecommendationWorkflowResultLike",
    "ScanWorkflowResultLike",
    "VerticalPlaylistFlow",
    "VerticalPlaylistFlowResult",
    "VerticalScanRecommendationResult",
]
