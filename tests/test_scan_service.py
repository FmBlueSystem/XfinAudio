import logging
from pathlib import Path

import pytest

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
