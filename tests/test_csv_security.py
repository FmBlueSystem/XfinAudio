"""All shared CSV reports keep metadata inert while JSON stays lossless."""

from __future__ import annotations

import csv
import json
from io import StringIO

import pytest

from xfinaudio.exporting.playlist_exporters import export_playlist_csv, export_playlist_json
from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.metadata_gaps import (
    build_metadata_gap_report,
    export_metadata_gap_report_csv,
    export_metadata_gap_report_json,
)
from xfinaudio.quality.dj_readiness import (
    DjReadinessCheck,
    DjReadinessReport,
    export_dj_readiness_csv,
    export_dj_readiness_json,
)
from xfinaudio.recommendation.playlist_service import recommend_playlist


@pytest.mark.parametrize(
    ("value", "escaped"),
    [
        (prefix + formula, True)
        for prefix in ("", " ", "\t", "\r", "\n", "\x00", "\u00a0", "\ufeff")
        for formula in ("=1+1", "+1+1", "-1+1", "@SUM(1,1)")
    ]
    + [
        (value, False)
        for value in (
            "Ordinary artist",
            "",
            "O'Brien",
            'Title, "quoted"\nsecond line',
            "First\rsecond line",
            "x=1",
            "  normal text",
            "\t\u00a0\ufeff",
            "'=1+1",
        )
    ],
)
def test_shared_csv_text_is_safe_and_json_is_lossless(value: str, escaped: bool) -> None:
    expected = "'" + value if escaped else value
    track = TrackRecord(path=value, title=value, artist=value, release_year=2001)
    gap_report = build_metadata_gap_report([track])
    recommendation = recommend_playlist([], "harmonic_journey").model_copy(
        update={"ordered_tracks": [track.model_copy(update={"bpm": 120.5, "energy_level": 7, "camelot_key": value})]}
    )
    readiness = DjReadinessReport(
        status="ready",
        summary="synthetic",
        blocker_count=0,
        review_count=0,
        checks=[DjReadinessCheck(label=value, status="ready", detail=value)],
    )

    gap_rows = list(csv.DictReader(StringIO(export_metadata_gap_report_csv(gap_report), newline="")))
    playlist_rows = list(csv.DictReader(StringIO(export_playlist_csv(recommendation), newline="")))
    readiness_rows = list(csv.DictReader(StringIO(export_dj_readiness_csv(readiness), newline="")))

    assert len(gap_rows) == len(playlist_rows) == len(readiness_rows) == 1
    for row in (gap_rows[0], playlist_rows[0]):
        for field in ("path", "title", "artist"):
            assert row[field] == expected
    assert playlist_rows[0]["camelot_key"] == expected
    assert playlist_rows[0]["order"] == "1"
    assert playlist_rows[0]["bpm"] == "120.5"
    assert playlist_rows[0]["energy_level"] == "7"
    assert gap_rows[0]["release_year"] == "2001"
    assert readiness_rows[0] == {"check": expected, "status": "ready", "detail": expected}

    gap_json = json.loads(export_metadata_gap_report_json(gap_report))
    playlist_json = json.loads(export_playlist_json(recommendation))
    readiness_json = json.loads(export_dj_readiness_json(readiness))
    for row in (gap_json["entries"][0], playlist_json["tracks"][0]):
        for field in ("path", "title", "artist"):
            assert row[field] == value
    assert readiness_json["checks"][0]["label"] == value
    assert readiness_json["checks"][0]["detail"] == value


def test_csv_encoder_does_not_turn_negative_numeric_columns_into_text() -> None:
    record = TrackRecord(path="normal.flac", bpm=-120.5, energy_level=-7, release_year=-1)
    recommendation = recommend_playlist([], "harmonic_journey").model_copy(update={"ordered_tracks": [record]})
    playlist_row = next(csv.DictReader(StringIO(export_playlist_csv(recommendation))))
    gap_row = next(csv.DictReader(StringIO(export_metadata_gap_report_csv(build_metadata_gap_report([record])))))

    assert playlist_row["bpm"] == "-120.5"
    assert playlist_row["energy_level"] == "-7"
    assert gap_row["release_year"] == "-1"
