"""Tests for LibraryFilter — pure filtering logic extracted from MainWindow."""

from __future__ import annotations

from xfinaudio.desktop.library_filter import (
    _duplicate_group_key,
    _normalize_artist_for_grouping,
    _normalize_title_for_grouping,
    _pick_duplicate_representative,
    _RowInfo,
    metadata_missing_field_records,
    metadata_status_records,
    suppressed_duplicate_paths,
)
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


# ---------------------------------------------------------------------------
# R1 — title/artist normalization for grouping
# ---------------------------------------------------------------------------


def test_normalize_title_strips_camelot_energy_suffix():
    assert _normalize_title_for_grouping("Right On Track - 12A - Energy 7") == "right on track"


def test_normalize_title_strips_single_digit_camelot_key():
    assert _normalize_title_for_grouping("Song - 1B - Energy 10") == "song"


def test_normalize_title_strips_version_suffix():
    assert _normalize_title_for_grouping("Right On Track (v2)") == "right on track"


def test_normalize_title_strips_both_suffixes_regardless_of_order():
    assert _normalize_title_for_grouping("Song - 8A - Energy 7 (v2)") == "song"
    assert _normalize_title_for_grouping("Song (v2) - 8A - Energy 7") == "song"


def test_normalize_title_strips_repeated_version_suffixes():
    assert _normalize_title_for_grouping("Song (v2) (v3) - 1B - Energy 10") == "song"


def test_normalize_title_preserves_remix_descriptor_content_but_strips_parens():
    # Parentheses are punctuation noise, stripped — but the descriptor's actual
    # content is never touched, only the "(" / ")" characters around it.
    assert (
        _normalize_title_for_grouping("Right On Track (kwikMIX by DJ Richie Rich)")
        == "right on track kwikmix by dj richie rich"
    )


def test_normalize_title_preserves_long_version_descriptor_content():
    assert _normalize_title_for_grouping("Song (Long Version)") == "song long version"


def test_normalize_title_preserves_clean_descriptor_content():
    assert _normalize_title_for_grouping("Song (Clean)") == "song clean"


def test_normalize_title_groups_parenthesized_and_bare_remix_descriptor_forms():
    # Regression for the CRITICAL found by Codex adversarial review: real-world
    # exports are inconsistent about wrapping the same remix descriptor in
    # parentheses. All three literal titles from the motivating screenshot must
    # normalize identically, or the feature fails on its own primary use case.
    parenthesized_v2 = _normalize_title_for_grouping("Right On Track (kwikMIX by DJ Richie Rich) (v2)")
    bare_with_technical_suffix = _normalize_title_for_grouping(
        "Right On Track Kwikmix By Dj Richie Rich - 12A - Energy 7"
    )
    parenthesized_plain = _normalize_title_for_grouping("Right On Track (Kwikmix By Dj Richie Rich)")
    assert (
        parenthesized_v2
        == bare_with_technical_suffix
        == parenthesized_plain
        == "right on track kwikmix by dj richie rich"
    )


def test_normalize_title_different_remix_descriptors_still_differ_after_paren_stripping():
    # Negative control: stripping parentheses must not cause DIFFERENT remixes/
    # edits of the same song to collapse into one group — only the punctuation
    # goes away, the descriptor content still has to differ or match on its own.
    kwikmix = _normalize_title_for_grouping("Billie Jean (kwikMIX by DJ Volume)")
    long_version = _normalize_title_for_grouping("Billie Jean (Long Version)")
    assert kwikmix != long_version


def test_normalize_title_does_not_falsely_strip_non_camelot_suffix():
    # "AB" is not a valid Camelot key shape (must be digit(s) + A/B) — must survive untouched.
    assert _normalize_title_for_grouping("Song - AB - Energy 7") == "song - ab - energy 7"


def test_normalize_title_strips_whitespace():
    assert _normalize_title_for_grouping("  Song  ") == "song"


def test_normalize_title_casefold_applied_after_suffix_stripping():
    # Regex is written against real-case "Energy"/"A"/"B" — casefolding first would break matching.
    assert _normalize_title_for_grouping("Track - 8A - Energy 7") == "track"


def test_normalize_artist_casefolds_and_strips_whitespace():
    assert _normalize_artist_for_grouping("  DJ Name  ") == "dj name"
    assert _normalize_artist_for_grouping("DJ NAME") == "dj name"


def test_normalize_artist_does_not_strip_suffixes():
    assert _normalize_artist_for_grouping("DJ Name - 8A - Energy 7") == "dj name - 8a - energy 7"


# ---------------------------------------------------------------------------
# R2 — blank/placeholder metadata never groups
# ---------------------------------------------------------------------------


def test_duplicate_group_key_none_when_title_none():
    assert _duplicate_group_key(None, "Artist") is None


def test_duplicate_group_key_none_when_artist_none():
    assert _duplicate_group_key("Title", None) is None


def test_duplicate_group_key_none_when_title_blank():
    assert _duplicate_group_key("   ", "Artist") is None


def test_duplicate_group_key_none_when_artist_blank():
    assert _duplicate_group_key("Title", "   ") is None


def test_duplicate_group_key_none_when_title_is_placeholder_dash():
    assert _duplicate_group_key("—", "Artist") is None


def test_duplicate_group_key_none_when_artist_is_placeholder_dash():
    assert _duplicate_group_key("Title", "—") is None


def test_duplicate_group_key_returns_normalized_tuple_for_valid_input():
    assert _duplicate_group_key("Song - 8A - Energy 7", "  DJ Name  ") == ("dj name", "song")


# ---------------------------------------------------------------------------
# R3 — representative selection
# ---------------------------------------------------------------------------


def _row(
    path: str,
    title: str = "Song",
    artist: str = "Artist",
    status: str = "incomplete",
    missing: int = 0,
) -> _RowInfo:
    return _RowInfo(title=title, artist=artist, status=status, missing_field_count=missing, path=path)


def test_pick_representative_prefers_complete_status():
    rows = [_row("/b.mp3", status="incomplete", missing=0), _row("/a.mp3", status="complete", missing=2)]
    assert _pick_duplicate_representative(rows).path == "/a.mp3"


def test_pick_representative_prefers_lower_missing_field_count_when_status_tied():
    rows = [_row("/b.mp3", status="incomplete", missing=2), _row("/a.mp3", status="incomplete", missing=0)]
    assert _pick_duplicate_representative(rows).path == "/a.mp3"


def test_pick_representative_prefers_shorter_title_when_status_and_missing_tied():
    rows = [
        _row("/b.mp3", title="Song Extended", status="incomplete", missing=0),
        _row("/a.mp3", title="Song", status="incomplete", missing=0),
    ]
    assert _pick_duplicate_representative(rows).path == "/a.mp3"


def test_pick_representative_uses_path_as_final_tiebreak():
    rows = [
        _row("/z.mp3", title="Song", status="incomplete", missing=0),
        _row("/a.mp3", title="Song", status="incomplete", missing=0),
    ]
    assert _pick_duplicate_representative(rows).path == "/a.mp3"


# ---------------------------------------------------------------------------
# suppressed_duplicate_paths — group semantics
# ---------------------------------------------------------------------------


def test_suppressed_duplicate_paths_singleton_untouched():
    rows = [_row("/a.mp3", title="Song A", artist="Artist"), _row("/b.mp3", title="Song B", artist="Artist")]
    assert suppressed_duplicate_paths(rows) == set()


def test_suppressed_duplicate_paths_suppresses_all_but_representative():
    rows = [
        _row("/a.mp3", title="Song - 8A - Energy 7", artist="Artist", status="complete", missing=0),
        _row("/b.mp3", title="Song (v2)", artist="Artist", status="incomplete", missing=2),
        _row("/c.mp3", title="Song", artist="Artist", status="incomplete", missing=1),
    ]
    assert suppressed_duplicate_paths(rows) == {"/b.mp3", "/c.mp3"}


def test_suppressed_duplicate_paths_blank_metadata_rows_never_suppressed():
    rows = [_row("/a.mp3", title="—", artist="Artist"), _row("/b.mp3", title="—", artist="Artist")]
    assert suppressed_duplicate_paths(rows) == set()


def test_suppressed_duplicate_paths_multiple_independent_groups():
    rows = [
        _row("/a1.mp3", title="Song A", artist="Artist", status="complete"),
        _row("/a2.mp3", title="Song A (v2)", artist="Artist", status="incomplete", missing=1),
        _row("/b1.mp3", title="Song B", artist="Artist", status="complete"),
        _row("/b2.mp3", title="Song B (v2)", artist="Artist", status="incomplete", missing=1),
    ]
    assert suppressed_duplicate_paths(rows) == {"/a2.mp3", "/b2.mp3"}


def test_suppressed_duplicate_paths_empty_input():
    assert suppressed_duplicate_paths([]) == set()
