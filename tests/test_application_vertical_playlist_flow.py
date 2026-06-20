"""Tests for the application-level vertical playlist flow."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist
from xfinaudio.library.scan_service import ScanCancellationToken, ScanProgress
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


@dataclass(frozen=True)
class FakeScanResult:
    records: list[TrackRecord]
    complete_count: int
    incomplete_count: int
    cancelled: bool = False


@dataclass(frozen=True)
class FakeRecommendationResult:
    recommendation: PlaylistRecommendation


@dataclass(frozen=True)
class FakeApplicationExportResult:
    requested_name: str


class FakePlaylistWorkflowService:
    def __init__(
        self,
        recommendation: PlaylistRecommendation,
        scan_result: FakeScanResult | None = None,
    ) -> None:
        self.recommendation = recommendation
        self.scan_result = scan_result
        self.scan_calls: list[tuple[Path, object | None, object | None, bool]] = []
        self.calls: list[tuple[list[TrackRecord], str, object | None, float]] = []

    def scan_folder(
        self,
        folder: Path,
        *,
        on_progress: object | None = None,
        cancellation_token: object | None = None,
        resolve_spectral_profiles: bool = True,
    ) -> FakeScanResult:
        self.scan_calls.append((folder, on_progress, cancellation_token, resolve_spectral_profiles))
        assert self.scan_result is not None
        return self.scan_result

    def recommend(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        controls: object | None = None,
        spectral_cohesion: float = 0.0,
    ) -> FakeRecommendationResult:
        self.calls.append((records, strategy_name, controls, spectral_cohesion))
        return FakeRecommendationResult(recommendation=self.recommendation)


class FakeSavedPlaylistService:
    def __init__(self) -> None:
        self.calls: list[tuple[PlaylistRecommendation, str | None]] = []
        self.export_calls: list[tuple[int, list[TrackRecord]]] = []
        self.playlist = Playlist(
            id=42,
            name="First Vertical",
            created_at=datetime(2026, 6, 20),
            updated_at=datetime(2026, 6, 20),
            track_paths=["/music/a.flac", "/music/b.flac"],
        )

    def save_recommendation(
        self,
        recommendation: PlaylistRecommendation,
        *,
        name: str | None = None,
    ) -> Playlist:
        self.calls.append((recommendation, name))
        return self.playlist

    def build_export_recommendation(
        self,
        playlist_id: int,
        scanned_records: list[TrackRecord],
    ):
        from xfinaudio.application import SavedPlaylistExport

        self.export_calls.append((playlist_id, scanned_records))
        return SavedPlaylistExport(playlist=self.playlist, recommendation=_recommendation())


class FakeApplicationExporter:
    def __init__(self) -> None:
        self.calls: list[tuple[PlaylistRecommendation, str]] = []

    def export_saved_playlist(
        self,
        *,
        recommendation: PlaylistRecommendation,
        requested_name: str,
    ) -> FakeApplicationExportResult:
        self.calls.append((recommendation, requested_name))
        return FakeApplicationExportResult(requested_name=requested_name)


def _recommendation() -> PlaylistRecommendation:
    tracks = [
        TrackRecord(path="/music/a.flac", title="A", metadata_status="complete"),
        TrackRecord(path="/music/b.flac", title="B", metadata_status="complete"),
    ]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=default_strategy_registry().get("warmup"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def test_vertical_playlist_flow_recommends_and_saves_without_desktop_imports() -> None:
    import xfinaudio.application.vertical_playlist_flow as vertical_playlist_flow
    from xfinaudio.application import VerticalPlaylistFlow

    source = inspect.getsource(vertical_playlist_flow)
    assert "xfinaudio.desktop" not in source
    assert "PySide6" not in source

    recommendation = _recommendation()
    workflow = FakePlaylistWorkflowService(recommendation)
    saved_playlists = FakeSavedPlaylistService()
    flow = VerticalPlaylistFlow(
        playlist_workflow=workflow,
        saved_playlists=saved_playlists,
    )

    result = flow.recommend_and_save(
        recommendation.ordered_tracks,
        "warmup",
        playlist_name="First Vertical",
    )

    assert workflow.calls == [(recommendation.ordered_tracks, "warmup", None, 0.0)]
    assert saved_playlists.calls == [(recommendation, "First Vertical")]
    assert result.recommendation is recommendation
    assert result.playlist == saved_playlists.playlist


def test_vertical_playlist_flow_scans_then_recommends_without_desktop_worker_ownership(tmp_path) -> None:
    import xfinaudio.application.vertical_playlist_flow as vertical_playlist_flow
    from xfinaudio.application import VerticalPlaylistFlow

    source = inspect.getsource(vertical_playlist_flow)
    assert "xfinaudio.desktop" not in source
    assert "PySide6" not in source

    scanned_records = [
        TrackRecord(path=str(tmp_path / "a.flac"), title="A", metadata_status="complete"),
        TrackRecord(path=str(tmp_path / "b.flac"), title="B", metadata_status="complete"),
    ]
    recommendation = PlaylistRecommendation(
        ordered_tracks=scanned_records,
        transition_scores=[],
        strategy=default_strategy_registry().get("warmup"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )
    scan_result = FakeScanResult(
        records=scanned_records,
        complete_count=2,
        incomplete_count=0,
    )
    workflow = FakePlaylistWorkflowService(recommendation, scan_result=scan_result)
    saved_playlists = FakeSavedPlaylistService()
    flow = VerticalPlaylistFlow(
        playlist_workflow=workflow,
        saved_playlists=saved_playlists,
    )
    progress_events: list[ScanProgress] = []
    progress_callback = progress_events.append
    cancellation_token = ScanCancellationToken()

    result = flow.scan_and_recommend(
        tmp_path,
        "warmup",
        on_progress=progress_callback,
        cancellation_token=cancellation_token,
        resolve_spectral_profiles=False,
    )

    assert workflow.scan_calls == [(tmp_path, progress_callback, cancellation_token, False)]
    assert workflow.calls == [(scanned_records, "warmup", None, 0.0)]
    assert saved_playlists.calls == []
    assert result.scan_result is scan_result
    assert result.recommendation_result.recommendation is recommendation
    assert result.recommendation is recommendation


def test_vertical_playlist_flow_exports_saved_playlist_with_playlist_name_as_export_name() -> None:
    import xfinaudio.application.vertical_playlist_flow as vertical_playlist_flow
    from xfinaudio.application import VerticalPlaylistFlow

    source = inspect.getsource(vertical_playlist_flow)
    assert "xfinaudio.desktop" not in source
    assert "PySide6" not in source

    recommendation = _recommendation()
    workflow = FakePlaylistWorkflowService(recommendation)
    saved_playlists = FakeSavedPlaylistService()
    exporter = FakeApplicationExporter()
    flow = VerticalPlaylistFlow(
        playlist_workflow=workflow,
        saved_playlists=saved_playlists,
        saved_playlist_exporter=exporter,
    )

    result = flow.export_saved_playlist(
        playlist_id=42,
        scanned_records=recommendation.ordered_tracks,
    )

    assert result is not None
    assert saved_playlists.export_calls == [(42, recommendation.ordered_tracks)]
    assert exporter.calls == [(result.recommendation, "First Vertical")]
    assert result.playlist == saved_playlists.playlist
    assert result.export_result == FakeApplicationExportResult(requested_name="First Vertical")
