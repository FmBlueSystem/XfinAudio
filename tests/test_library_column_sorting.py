"""Every public data column sorts the entire local match set without side effects."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import _public_track
from xfinaudio.headless.library_browse import LibraryBrowser
from xfinaudio.library.models import TrackRecord


@pytest.mark.parametrize(
    ("field", "values"),
    [
        ("title", ["alpha", "Bravo", "zulu"]),
        ("artist", ["alpha", "Bravo", "zulu"]),
        ("genre", ["ambient", "House", "Techno"]),
        ("bpm", [9, 80, 120]),
        ("key", ["2A", "2B", "10A"]),
        ("energy", [2, 5, 10]),
        ("duration", [9, 80, 120]),
        ("format", ["AIFF", "FLAC", "MP4"]),
        ("bitrate", [9, 128, 1411.2]),
    ],
)
def test_each_column_both_directions_has_numeric_order_nulls_last_and_stable_ties(field, values):
    attribute = {
        "key": "camelot_key",
        "energy": "energy_level",
        "format": "audio_format",
        "bitrate": "bitrate_kbps",
    }.get(field, field)
    records = [TrackRecord(path=f"/{i:03}.flac", **{attribute: value}) for i, value in enumerate(values)]
    records += [TrackRecord(path="/tie.flac", **{attribute: values[1]}), TrackRecord(path="/missing.flac")]
    original = list(reversed(records))
    browser = LibraryBrowser(cast(HeadlessBackend, SimpleNamespace(_records=lambda: original)))
    for descending, order in ((False, [0, 1, 3, 2, 4]), (True, [2, 1, 3, 0, 4])):
        result = browser.execute("library.query", {"sortBy": field, "descending": descending})
        expected = [records[i].path for i in order]
        assert [track["id"] for track in result["tracks"]] == [
            _public_track(TrackRecord(path=p))["id"] for p in expected
        ]
        assert original == list(reversed(records)), "Sorting must not reorder recommendation input"


def test_sort_covers_all_filtered_rows_and_preserves_duplicate_rules():
    records = [
        TrackRecord(path=f"/{i:04}.flac", title=f"Track {i}", genre="House" if i % 2 else "Techno", bitrate_kbps=i + 1)
        for i in range(650)
    ]
    browser = LibraryBrowser(cast(HeadlessBackend, SimpleNamespace(_records=lambda: records)))
    result = browser.execute("library.query", {"query": {"genre": "House"}, "sortBy": "bitrate", "descending": True})
    assert result["matchedCount"] == 325
    assert [row["bitrateKbps"] for row in result["tracks"]] == list(range(650, 0, -2))
    assert result["query"]["genre"] == "House"


def test_format_sort_distinguishes_container_codec_and_missing_text():
    records = [
        TrackRecord(path="/z.m4a", audio_format="MP4", audio_codec="AAC LC"),
        TrackRecord(path="/a.m4a", audio_format="MP4", audio_codec="ALAC"),
        TrackRecord(path="/blank.flac", audio_format=" "),
    ]
    browser = LibraryBrowser(cast(HeadlessBackend, SimpleNamespace(_records=lambda: records)))
    for descending, expected in ((False, ["AAC LC", "ALAC", None]), (True, ["ALAC", "AAC LC", None])):
        rows = browser.execute("library.query", {"sortBy": "format", "descending": descending})["tracks"]
        assert [row["audioCodec"] for row in rows] == expected
