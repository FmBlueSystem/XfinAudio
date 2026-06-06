"""End-to-end integration: scan -> persist -> recommend -> Serato export.

Exercises the real PlaylistWorkflowService, TrackRepository, scan_folder, and
Serato crate writer together. Only the scanner's path-discovery and tag-reading
seams are stubbed, so metadata parsing, persistence, recommendation, and crate
writing all run against real implementations.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes, write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import plan_serato_playlist_export
from xfinaudio.library.scan_service import ScanCancellationToken, ScanProgress, scan_folder
from xfinaudio.library.track_repository import TrackRepository


class _SeededScanService:
    """Real scan_folder driven by deterministic in-memory tags for integration tests."""

    def __init__(self, tags_by_path: dict[Path, dict[str, Any]]) -> None:
        self._tags_by_path = tags_by_path

    def scan(
        self,
        folder: Path,
        *,
        on_progress: Any = None,
        cancellation_token: ScanCancellationToken | None = None,
    ) -> list:
        def list_paths(_folder: Path) -> Iterable[Path]:
            return list(self._tags_by_path.keys())

        def read_tags(path: Path) -> dict[str, Any] | None:
            return self._tags_by_path.get(path)

        return scan_folder(
            folder,
            list_paths=list_paths,
            read_tags=read_tags,
            on_progress=on_progress,
            cancellation_token=cancellation_token,
        )


def _complete_tags(title: str, bpm: str, key: str, energy: str) -> dict[str, list[str]]:
    return {
        "title": [title],
        "artist": ["Integration Artist"],
        "bpm": [bpm],
        "initialkey": [key],
        "energylevel": [energy],
        "genre": ["House"],
    }


def test_scan_persist_recommend_export_end_to_end(tmp_path: Path) -> None:
    volume = tmp_path / "dd"
    audio_dir = volume / "_Lossless"
    audio_dir.mkdir(parents=True)
    track_a = audio_dir / "A.mp3"
    track_b = audio_dir / "B.mp3"
    incomplete = audio_dir / "C.mp3"

    tags_by_path: dict[Path, dict[str, Any]] = {
        track_a: _complete_tags("A", "120", "8A", "7"),
        track_b: _complete_tags("B", "122", "9A", "6"),
        incomplete: {"title": ["C"], "bpm": ["124"], "initialkey": ["10A"]},
    }

    repository = TrackRepository(tmp_path / "library.db")
    workflow = PlaylistWorkflowService(scan_service=_SeededScanService(tags_by_path), repository=repository)

    scan_result = workflow.scan_folder(audio_dir)

    assert scan_result.complete_count == 2
    assert scan_result.incomplete_count == 1

    persisted = repository.list_tracks()
    assert len(persisted) == 3

    rec_result = workflow.recommend(persisted, "build")
    recommended_paths = [track.path for track in rec_result.recommendation.ordered_tracks]

    assert str(incomplete) not in recommended_paths
    assert set(recommended_paths) == {str(track_a), str(track_b)}

    serato_folder = volume / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    plan = plan_serato_playlist_export("Integration Set", rec_result.recommendation, serato_folder)
    write_result = write_serato_crate(plan, confirm=True)

    assert write_result.validated is True
    parsed = parse_serato_crate_bytes(write_result.written_path.read_bytes())
    assert parsed.paths == plan.relative_paths
    assert set(parsed.paths) == {"_Lossless/A.mp3", "_Lossless/B.mp3"}


def test_incomplete_metadata_excluded_from_recommendation_after_real_scan(tmp_path: Path) -> None:
    audio_dir = tmp_path / "dd" / "_Lossless"
    audio_dir.mkdir(parents=True)
    complete = audio_dir / "complete.mp3"
    missing_energy = audio_dir / "missing_energy.mp3"

    tags_by_path: dict[Path, dict[str, Any]] = {
        complete: _complete_tags("Complete", "128", "11A", "8"),
        missing_energy: {"title": ["Missing Energy"], "bpm": ["128"], "initialkey": ["11A"]},
    }

    progress_events: list[ScanProgress] = []
    repository = TrackRepository(tmp_path / "library.db")
    workflow = PlaylistWorkflowService(scan_service=_SeededScanService(tags_by_path), repository=repository)

    workflow.scan_folder(audio_dir, on_progress=progress_events.append)

    assert len(progress_events) == 2

    persisted = repository.list_tracks()
    statuses = {record.path: record.metadata_status for record in persisted}
    assert statuses[str(complete)] == "complete"
    assert statuses[str(missing_energy)] == "incomplete"

    rec_result = workflow.recommend(persisted, "build")
    recommended_paths = [track.path for track in rec_result.recommendation.ordered_tracks]

    assert recommended_paths == [str(complete)]
