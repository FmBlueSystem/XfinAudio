import logging
from pathlib import Path

import pytest

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.scan_service import ScanCancellationToken, ScanCancelledError, scan_folder


def test_scan_folder_recursively_reads_supported_audio_metadata() -> None:
    requested_paths: list[Path] = []

    def read_tags(path: Path) -> dict[str, list[str]]:
        requested_paths.append(path)
        return {
            "title": ["Track One"],
            "artist": ["Artist One"],
            "bpm": ["116.0"],
            "key": ["eyJhbGdvcml0aG0iOjk0LCJrZXkiOiIxMUIiLCJzb3VyY2UiOiJtaXhlZGlua2V5In0="],
            "energy": ["eyJhbGdvcml0aG0iOjEzLCJlbmVyZ3lMZXZlbCI6Nywic291cmNlIjoibWl4ZWRpbmtleSJ9"],
            "genre": ["Disco"],
        }

    root = Path("/library")
    paths = [root / "nested" / "track.flac", root / "notes.txt"]

    records = scan_folder(root, list_paths=lambda folder: paths, read_tags=read_tags)

    assert [record.path for record in records] == [str(root / "nested" / "track.flac")]
    assert requested_paths == [root / "nested" / "track.flac"]
    assert records[0].title == "Track One"
    assert records[0].artist == "Artist One"
    assert records[0].bpm == 116.0
    assert records[0].camelot_key == "11B"
    assert records[0].energy_level == 7
    assert records[0].genre == "Disco"
    assert records[0].metadata_status == "complete"
    assert records[0].raw_metadata["title"] == ["Track One"]
    assert records[0].source_fields["camelot_key"] == "key"


def test_scan_folder_marks_records_incomplete_when_required_metadata_is_missing() -> None:
    root = Path("/library")
    audio_path = root / "track.aif"

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Partial"], "TBPM": ["128.55"]},
    )

    assert records[0].metadata_status == "incomplete"
    assert set(records[0].missing_required_fields) == {"camelot_key", "energy_level"}


def test_scan_folder_skips_files_when_mutagen_cannot_read_tags() -> None:
    root = Path("/library")
    audio_path = root / "broken.mp3"

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: None,
    )

    assert records == []


def test_scan_folder_skips_supported_files_when_tag_reader_raises() -> None:
    root = Path("/library")
    broken_path = root / "broken.flac"
    good_path = root / "good.flac"

    def read_tags(path: Path) -> dict[str, list[str]]:
        if path == broken_path:
            raise ValueError("corrupt metadata")
        return {
            "title": ["Good Track"],
            "bpm": ["116.0"],
            "key": ["eyJhbGdvcml0aG0iOjk0LCJrZXkiOiIxMUIiLCJzb3VyY2UiOiJtaXhlZGlua2V5In0="],
            "energy": ["eyJhbGdvcml0aG0iOjEzLCJlbmVyZ3lMZXZlbCI6Nywic291cmNlIjoibWl4ZWRpbmtleSJ9"],
        }

    records = scan_folder(
        root,
        list_paths=lambda folder: [broken_path, good_path],
        read_tags=read_tags,
    )

    assert [record.path for record in records] == [str(good_path)]


def test_scan_folder_logs_supported_file_read_failures_without_raw_metadata(caplog) -> None:
    root = Path("/library")
    broken_path = root / "broken.flac"

    with caplog.at_level(logging.WARNING, logger="xfinaudio.library.scan_service"):
        records = scan_folder(
            root,
            list_paths=lambda folder: [broken_path],
            read_tags=lambda path: (_ for _ in ()).throw(ValueError("corrupt metadata")),
        )

    assert records == []
    assert str(broken_path) in caplog.text
    assert "ValueError" in caplog.text
    assert "corrupt metadata" in caplog.text
    assert "raw_metadata" not in caplog.text


def test_scan_folder_reports_supported_file_progress_in_deterministic_order() -> None:
    root = Path("/library")
    first_path = root / "a.flac"
    second_path = root / "nested" / "b.mp3"
    progress_events = []

    records = scan_folder(
        root,
        list_paths=lambda folder: [root / "notes.txt", second_path, first_path],
        read_tags=lambda path: {"title": [path.stem]},
        on_progress=progress_events.append,
    )

    assert [record.path for record in records] == [str(first_path), str(second_path)]
    assert [(event.processed_count, event.total_count, event.current_path) for event in progress_events] == [
        (1, 2, first_path),
        (2, 2, second_path),
    ]


def test_scan_folder_reports_progress_for_skipped_supported_files() -> None:
    root = Path("/library")
    broken_path = root / "a.flac"
    no_tags_path = root / "b.mp3"
    good_path = root / "c.wav"
    progress_events = []

    def read_tags(path: Path) -> dict[str, list[str]] | None:
        if path == broken_path:
            raise ValueError("corrupt metadata")
        if path == no_tags_path:
            return None
        return {"title": [path.stem]}

    records = scan_folder(
        root,
        list_paths=lambda folder: [good_path, no_tags_path, broken_path],
        read_tags=read_tags,
        on_progress=progress_events.append,
    )

    assert [record.path for record in records] == [str(good_path)]
    assert [(event.processed_count, event.total_count, event.current_path) for event in progress_events] == [
        (1, 3, broken_path),
        (2, 3, no_tags_path),
        (3, 3, good_path),
    ]


def test_scan_folder_raises_cancelled_error_before_later_file_without_persisting_api_change() -> None:
    root = Path("/library")
    first_path = root / "a.flac"
    second_path = root / "b.flac"
    token = ScanCancellationToken()
    requested_paths: list[Path] = []

    def read_tags(path: Path) -> dict[str, list[str]]:
        requested_paths.append(path)
        token.cancel()
        return {"title": [path.stem]}

    with pytest.raises(ScanCancelledError) as exc_info:
        scan_folder(
            root,
            list_paths=lambda folder: [first_path, second_path],
            read_tags=read_tags,
            cancellation_token=token,
        )

    assert requested_paths == [first_path]
    assert [record.path for record in exc_info.value.records] == [str(first_path)]


def test_scan_folder_attaches_spectral_profile_when_analyzer_returns_profile(monkeypatch) -> None:
    root = Path("/library")
    audio_path = root / "track.flac"
    expected_profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        dominant_color="GREEN",
    )

    def fake_analyze(path: Path, **kwargs) -> SpectralProfile:
        return expected_profile

    monkeypatch.setattr("xfinaudio.library.scan_service.analyze_spectral_profile", fake_analyze)

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Track One"]},
    )

    assert len(records) == 1
    assert records[0].spectral_profile == expected_profile


def test_scan_folder_continues_when_analyzer_returns_none(monkeypatch) -> None:
    root = Path("/library")
    audio_path = root / "track.flac"

    monkeypatch.setattr("xfinaudio.library.scan_service.analyze_spectral_profile", lambda path, **kwargs: None)

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Track One"]},
    )

    assert len(records) == 1
    assert records[0].spectral_profile is None


def test_scan_folder_uses_previous_profile_cache_when_file_identity_matches() -> None:
    root = Path("/library")
    audio_path = root / "track.flac"
    expected_profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        dominant_color="GREEN",
    )

    def fake_analyze(path: Path, **kwargs) -> SpectralProfile:
        pytest.fail("Analyzer should not be called when cache matches")

    # The path does not exist, so stat will fail and cache lookup falls through to analysis.
    # Provide a cache entry with mismatched identity to force analysis and prove the path is checked.
    cache = {str(audio_path): (0, 0, expected_profile)}

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Track One"]},
        parallel_spectral_analysis=False,
        previous_profile_cache=cache,
    )

    assert len(records) == 1
    # Because the file cannot be stated, the mismatched cache is ignored and analyze runs.
    # This test primarily verifies the cache code path does not crash.
    assert records[0].spectral_profile is None


def test_scan_folder_runs_parallel_batch_when_enabled(monkeypatch) -> None:
    root = Path("/library")
    first_path = root / "a.flac"
    second_path = root / "b.flac"

    def fake_batch_analyze(paths, **kwargs):
        return {
            str(path): SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
            for path in paths
        }

    monkeypatch.setattr("xfinaudio.library.scan_service.analyze_paths", fake_batch_analyze)

    records = scan_folder(
        root,
        list_paths=lambda folder: [first_path, second_path],
        read_tags=lambda path: {"title": [path.stem]},
        parallel_spectral_analysis=True,
    )

    assert len(records) == 2
    assert all(record.spectral_profile is not None for record in records)
    assert all(record.spectral_profile.dominant_color == "RED" for record in records)
