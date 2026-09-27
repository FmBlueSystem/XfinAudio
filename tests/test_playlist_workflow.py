from collections.abc import Callable
from pathlib import Path
from typing import cast

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken, ScanCancelledError, ScanProgress
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.loudness_policy import LoudnessBand
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
        self.pruned_root: Path | str | None = None

    def save_scan_results(
        self,
        records: list[TrackRecord],
        *,
        pruned_root: Path | str | None = None,
    ) -> None:
        self.saved_records = list(records)
        self.pruned_root = pruned_root


def loudness_record(path: str, lufs: float) -> TrackRecord:
    return TrackRecord(
        path=path,
        bpm=124.0,
        camelot_key="8A",
        energy_level=5,
        metadata_status="complete",
        loudness_profile=LoudnessProfile(
            lufs_integrated=lufs,
            loudness_range_lra=4.0,
            true_peak_dbtp=-1.0,
            status=LoudnessStatus.MEASURED,
            engine_fingerprint="ffmpeg-test",
        ),
    )


def test_playlist_workflow_scan_folder_returns_counts_and_persists_records(tmp_path) -> None:
    repository = FakeRepository()
    workflow = PlaylistWorkflowService(scan_service=FakeScanService(), repository=repository)

    result = workflow.scan_folder(tmp_path)

    assert result.records == repository.saved_records
    assert result.complete_count == 1
    assert result.incomplete_count == 1
    assert result.cancelled is False
    assert repository.pruned_root == tmp_path


def test_playlist_workflow_scan_keeps_identity_matched_stale_profile_attached(tmp_path) -> None:
    from xfinaudio.library.track_repository import TrackRepository

    audio_file = tmp_path / "a.flac"
    audio_file.write_text("audio")
    stale = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    repository = TrackRepository(tmp_path / "library.db")
    repository.save_scan_results([TrackRecord(path=str(audio_file), spectral_profile=stale)])

    result = PlaylistWorkflowService(scan_service=FakeScanService(), repository=repository).scan_folder(
        tmp_path, resolve_spectral_profiles=False
    )

    matched = next(record for record in result.records if record.path == str(audio_file))
    assert matched.spectral_profile == stale


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
    forwarded = cast(Callable[[ScanProgress], None], scan_service.progress_callback)
    forwarded(ScanProgress(processed_count=1, total_count=2, current_path=tmp_path / "a.flac"))
    assert len(progress_events) == 1
    assert scan_service.cancellation_token is token


class RecordingFakeRepository:
    """Record every save call so batching order and pruning can be asserted."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[TrackRecord], Path | str | None]] = []

    def save_scan_results(
        self,
        records: list[TrackRecord],
        *,
        pruned_root: Path | str | None = None,
    ) -> None:
        self.calls.append((list(records), pruned_root))

    def _shapes(self) -> list[tuple[int, Path | str | None]]:
        return [(len(batch), pruned_root) for batch, pruned_root in self.calls]


class ProgressEmittingFakeScanService:
    """Emit one record-carrying progress event per scanned file."""

    def __init__(self, count: int, *, cancels_after_events: bool = False) -> None:
        self.count = count
        self.cancels_after_events = cancels_after_events

    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        callback = kwargs["on_progress"]
        records = [
            TrackRecord(
                path=str(folder / f"{index:03d}.flac"),
                bpm=120.0 + index,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
            for index in range(self.count)
        ]
        for index, record in enumerate(records, start=1):
            callback(
                ScanProgress(
                    processed_count=index,
                    total_count=len(records),
                    current_path=Path(record.path),
                    record=record,
                )
            )
        if self.cancels_after_events:
            raise ScanCancelledError(records)
        return records


def test_playlist_workflow_flushes_scan_batches_before_the_final_pruned_save(tmp_path) -> None:
    repository = RecordingFakeRepository()
    workflow = PlaylistWorkflowService(scan_service=ProgressEmittingFakeScanService(5), repository=repository)

    result = workflow.scan_folder(tmp_path, flush_batch_size=2, flush_interval_seconds=60.0)

    # Two full batches are upserted without a prune root while the scan runs;
    # only the completion save may delete rows, and it carries the root.
    assert repository._shapes() == [(2, None), (2, None), (5, tmp_path)]
    assert repository.calls[0][0] == result.records[:2]
    assert repository.calls[1][0] == result.records[2:4]
    assert result.persisted_record_count == 4


def test_playlist_workflow_flushes_scan_batches_on_the_interval_without_a_ui_callback(tmp_path) -> None:
    repository = RecordingFakeRepository()
    workflow = PlaylistWorkflowService(scan_service=ProgressEmittingFakeScanService(3), repository=repository)

    result = workflow.scan_folder(tmp_path, flush_batch_size=1000, flush_interval_seconds=0.0)

    assert repository._shapes() == [(1, None), (1, None), (1, None), (3, tmp_path)]
    assert result.persisted_record_count == 3


def test_playlist_workflow_skips_incremental_saves_for_progress_without_records(tmp_path) -> None:
    class RecordlessFakeScanService:
        def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
            callback = kwargs["on_progress"]
            records = [TrackRecord(path=str(folder / "a.flac"), metadata_status="complete")]
            callback(ScanProgress(processed_count=1, total_count=2, current_path=folder / "a.flac"))
            return records

    repository = RecordingFakeRepository()
    workflow = PlaylistWorkflowService(scan_service=RecordlessFakeScanService(), repository=repository)

    result = workflow.scan_folder(tmp_path, flush_batch_size=1, flush_interval_seconds=0.0)

    assert repository._shapes() == [(1, tmp_path)]
    assert result.persisted_record_count == 0


def test_playlist_workflow_cancelled_scan_keeps_incrementally_flushed_records(tmp_path) -> None:
    repository = RecordingFakeRepository()
    workflow = PlaylistWorkflowService(
        scan_service=ProgressEmittingFakeScanService(3, cancels_after_events=True), repository=repository
    )

    result = workflow.scan_folder(tmp_path, flush_batch_size=2, flush_interval_seconds=60.0)

    assert result.cancelled is True
    assert len(result.records) == 3
    # The flush that already happened stays on disk; a cancel never prunes.
    assert repository._shapes() == [(2, None)]
    assert result.persisted_record_count == 2


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


def test_playlist_workflow_applies_supplied_loudness_band_at_strategy_boundary() -> None:
    records = [loudness_record("/warmup.flac", -14.0), loudness_record("/peak.flac", -10.0)]
    workflow = PlaylistWorkflowService(scan_service=FakeScanService(), repository=FakeRepository())

    result = workflow.recommend(records, "consistent_loudness", loudness_band=LoudnessBand(-14.0, 0.5))

    assert [record.path for record in result.recommendation.ordered_tracks] == ["/warmup.flac"]
