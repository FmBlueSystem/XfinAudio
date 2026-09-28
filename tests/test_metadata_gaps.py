"""Tests for the deterministic metadata gap report.

The report is pure domain: it reads the parser's existing completeness signal
and never introduces a new completeness rule. release_year is informational only
and must never change which tracks appear as gaps.
"""

from __future__ import annotations

import csv
import json
from io import StringIO

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.metadata_gaps import (
    MetadataGapReport,
    build_metadata_gap_report,
    export_metadata_gap_report_csv,
    export_metadata_gap_report_json,
)


def _record(
    path: str,
    *,
    bpm: float | None = None,
    camelot_key: str | None = None,
    energy_level: int | None = None,
    release_year: int | None = None,
    title: str | None = None,
    artist: str | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=artist,
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        release_year=release_year,
    )


def _complete(
    path: str,
    *,
    title: str | None = None,
    artist: str | None = None,
    release_year: int | None = None,
) -> TrackRecord:
    return _record(
        path,
        bpm=120.0,
        camelot_key="8A",
        energy_level=7,
        title=title,
        artist=artist,
        release_year=release_year,
    )


def _mixed_library() -> list[TrackRecord]:
    return [
        _complete("/music/d.flac", title="D", artist="Artist D"),
        _record("/music/c.flac", bpm=120.0, title="C", artist="Artist C", release_year=1999),
        _complete("/music/a.flac", title="A", artist="Artist A", release_year=2001),
        _record("/music/b.flac", camelot_key="8A", energy_level=7, title="B", artist="Artist B"),
    ]


def test_empty_library_reports_zero_counts_and_no_entries() -> None:
    report = build_metadata_gap_report([])

    assert report.total_tracks == 0
    assert report.complete_count == 0
    assert report.incomplete_count == 0
    assert (report.gaps.bpm, report.gaps.camelot_key, report.gaps.energy_level) == (0, 0, 0)
    assert (report.year_coverage.with_release_year, report.year_coverage.without_release_year) == (0, 0)
    assert report.entries == []


def test_mixed_library_reports_exact_counts_and_gap_membership() -> None:
    report = build_metadata_gap_report(_mixed_library())

    assert report.total_tracks == 4
    assert report.complete_count == 2
    assert report.incomplete_count == 2
    assert (report.gaps.bpm, report.gaps.camelot_key, report.gaps.energy_level) == (1, 1, 1)
    assert (report.year_coverage.with_release_year, report.year_coverage.without_release_year) == (2, 2)
    assert [entry.path for entry in report.entries] == ["/music/b.flac", "/music/c.flac"]


def test_gap_entries_order_by_path_and_sort_missing_fields() -> None:
    report = build_metadata_gap_report(_mixed_library())

    by_path = {entry.path: entry for entry in report.entries}
    assert by_path["/music/b.flac"].missing_fields == ["bpm"]
    assert by_path["/music/c.flac"].missing_fields == ["camelot_key", "energy_level"]
    assert [entry.path for entry in report.entries] == sorted(entry.path for entry in report.entries)


def test_year_presence_never_changes_gap_membership() -> None:
    without_year = build_metadata_gap_report([_record("/music/x.flac", bpm=120.0)])
    with_year = build_metadata_gap_report([_record("/music/x.flac", bpm=120.0, release_year=2001)])

    assert [entry.path for entry in without_year.entries] == ["/music/x.flac"]
    assert [entry.path for entry in with_year.entries] == ["/music/x.flac"]
    expected = ["camelot_key", "energy_level"]
    assert without_year.entries[0].missing_fields == expected
    assert with_year.entries[0].missing_fields == expected


def test_complete_track_never_appears_even_with_a_release_year() -> None:
    report = build_metadata_gap_report([_complete("/music/complete.flac", release_year=2003)])

    assert report.entries == []
    assert report.complete_count == 1
    assert report.year_coverage.with_release_year == 1


def test_report_is_deterministic_across_repeated_builds() -> None:
    first = build_metadata_gap_report(_mixed_library())
    second = build_metadata_gap_report(_mixed_library())

    assert first.model_dump_json() == second.model_dump_json()
    assert export_metadata_gap_report_json(first) == export_metadata_gap_report_json(second)
    assert export_metadata_gap_report_csv(first) == export_metadata_gap_report_csv(second)


def test_export_json_round_trips_the_report_payload() -> None:
    report = build_metadata_gap_report(_mixed_library())

    payload = json.loads(export_metadata_gap_report_json(report))

    assert payload["total_tracks"] == 4
    assert payload["complete_count"] == 2
    assert payload["incomplete_count"] == 2
    assert payload["gaps"] == {"bpm": 1, "camelot_key": 1, "energy_level": 1}
    assert payload["year_coverage"] == {"with_release_year": 2, "without_release_year": 2}
    assert [entry["path"] for entry in payload["entries"]] == ["/music/b.flac", "/music/c.flac"]
    assert payload["entries"][1]["missing_fields"] == ["camelot_key", "energy_level"]
    assert payload["entries"][1]["release_year"] == 1999


def test_export_json_is_stable_text_with_trailing_newline() -> None:
    report = build_metadata_gap_report(_mixed_library())

    text = export_metadata_gap_report_json(report)

    assert text.endswith("\n")
    assert json.loads(text) == json.loads(export_metadata_gap_report_json(report))


def test_export_csv_has_one_row_per_gapped_track() -> None:
    report = build_metadata_gap_report(_mixed_library())

    rows = list(csv.DictReader(StringIO(export_metadata_gap_report_csv(report))))

    assert [row["path"] for row in rows] == ["/music/b.flac", "/music/c.flac"]
    assert rows[0]["missing_fields"] == "bpm"
    assert rows[1]["missing_fields"] == "camelot_key;energy_level"
    assert rows[1]["title"] == "C"
    assert rows[1]["artist"] == "Artist C"
    assert rows[1]["release_year"] == "1999"


def test_export_csv_leaves_release_year_empty_when_absent() -> None:
    report = build_metadata_gap_report([_record("/music/b.flac", title="B", artist="Artist B")])

    rows = list(csv.DictReader(StringIO(export_metadata_gap_report_csv(report))))

    assert rows[0]["release_year"] == ""


def test_export_csv_with_no_gaps_is_header_only() -> None:
    report = build_metadata_gap_report([_complete("/music/a.flac")])

    text = export_metadata_gap_report_csv(report)

    assert text.splitlines() == ["path,title,artist,missing_fields,release_year"]


def test_report_returns_typed_frozen_models() -> None:
    report = build_metadata_gap_report(_mixed_library())

    assert isinstance(report, MetadataGapReport)
    assert report.entries[0].missing_fields is not report.entries[1].missing_fields
