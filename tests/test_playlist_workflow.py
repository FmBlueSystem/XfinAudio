from pathlib import Path

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken, ScanCancelledError, ScanProgress
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class FakeScanService:
    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        return [
            TrackRecord(
                path=str(folder / "a.flac"),
                bpm=124.0,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            ),
            TrackRecord(path=str(folder / "b.flac"), metadata_status="incomplete"),
        ]


class FakeRepository:
    def __init__(self) -> None:
        self.saved_records: list[TrackRecord] = []

    def save_scan_results(self, records: list[TrackRecord]) -> None:
        self.saved_records = list(records)


def test_playlist_workflow_scan_folder_returns_counts_and_persists_records(tmp_path) -> None:
    repository = FakeRepository()
    workflow = PlaylistWorkflowService(scan_service=FakeScanService(), repository=repository)

    result = workflow.scan_folder(tmp_path)

    assert result.records == repository.saved_records
    assert result.complete_count == 1
    assert result.incomplete_count == 1
    assert result.cancelled is False


class CancellableFakeScanService:
    def __init__(self) -> None:
        self.progress_callback = None
        self.cancellation_token = None
        self.partial_records = [TrackRecord(path="/library/a.flac", metadata_status="complete")]

    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        self.progress_callback = kwargs["on_progress"]
        self.cancellation_token = kwargs["cancellation_token"]
        raise ScanCancelledError(self.partial_records)


def test_playlist_workflow_cancelled_scan_does_not_persist_partial_results(tmp_path) -> None:
    scan_service = CancellableFakeScanService()
    repository = FakeRepository()
    workflow = PlaylistWorkflowService(scan_service=scan_service, repository=repository)
    progress_events: list[ScanProgress] = []
    token = ScanCancellationToken()

    result = workflow.scan_folder(tmp_path, on_progress=progress_events.append, cancellation_token=token)

    assert result.cancelled is True
    assert result.records == scan_service.partial_records
    assert result.complete_count == 0
    assert result.incomplete_count == 0
    assert repository.saved_records == []
    assert scan_service.progress_callback == progress_events.append
    assert scan_service.cancellation_token is token


def test_workflow_forwards_dj_controls_to_recommendation() -> None:
    from xfinaudio.recommendation.controls import DJControls

    service = PlaylistWorkflowService(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(path="/a.flac", bpm=120.0, camelot_key="8A", energy_level=5, metadata_status="complete"),
        TrackRecord(path="/b.flac", bpm=120.0, camelot_key="8A", energy_level=5, metadata_status="complete"),
    ]

    result = service.recommend(records, "harmonic_journey", controls=DJControls(start_path="/b.flac"))

    assert result.recommendation.ordered_tracks[0].path == "/b.flac"
    assert result.recommendation.applied_controls["start_path"] == "/b.flac"


def test_playlist_workflow_recommend_returns_recommendation_explanation_and_quality_report(tmp_path) -> None:
    records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            bpm=125.0,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        ),
    ]
    workflow = PlaylistWorkflowService(scan_service=FakeScanService(), repository=FakeRepository())

    result = workflow.recommend(records, "harmonic_journey")

    assert isinstance(result.recommendation, PlaylistRecommendation)
    assert isinstance(result.explanation, PlaylistExplanation)
    assert isinstance(result.quality_report, RecommendationQualityReport)
    assert result.explanation.track_count == 2
    assert result.quality_report.track_count == 2
