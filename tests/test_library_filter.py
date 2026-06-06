"""Tests for LibraryFilter — pure filtering logic extracted from MainWindow."""

from __future__ import annotations

from xfinaudio.desktop.library_filter import metadata_missing_field_records, metadata_status_records

from xfinaudio.library.models import TrackRecord


def _record(path: str, status: str, missing: list[str] | None = None) -> TrackRecord:
    return TrackRecord(
        path=path,
        metadata_status=status,  # type: ignore[arg-type]
        missing_required_fields=missing or [],
    )


RECORDS = [
    _record("/a.mp3", "complete"),
    _record("/b.mp3", "incomplete", ["bpm"]),
    _record("/c.mp3", "incomplete", ["bpm", "camelot_key"]),
    _record("/d.mp3", "complete"),
]


def test_metadata_status_records_filters_complete():
    result = metadata_status_records(RECORDS, "complete")
    assert [r.path for r in result] == ["/a.mp3", "/d.mp3"]


def test_metadata_status_records_filters_incomplete():
    result = metadata_status_records(RECORDS, "incomplete")
    assert [r.path for r in result] == ["/b.mp3", "/c.mp3"]


def test_metadata_status_records_empty_on_no_match():
    assert metadata_status_records(RECORDS, "unknown") == []


def test_metadata_status_records_empty_input():
    assert metadata_status_records([], "complete") == []


def test_metadata_missing_field_records_filters_by_field():
    result = metadata_missing_field_records(RECORDS, "bpm")
    assert [r.path for r in result] == ["/b.mp3", "/c.mp3"]


def test_metadata_missing_field_records_specific_field():
    result = metadata_missing_field_records(RECORDS, "camelot_key")
    assert [r.path for r in result] == ["/c.mp3"]


def test_metadata_missing_field_records_excludes_complete_tracks():
    result = metadata_missing_field_records(RECORDS, "bpm")
    assert all(r.metadata_status == "incomplete" for r in result)


def test_metadata_missing_field_records_no_match():
    assert metadata_missing_field_records(RECORDS, "energy_level") == []
