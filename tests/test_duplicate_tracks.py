"""Tests for deterministic repeated-track detection in generated playlists."""

from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.duplicate_tracks import (
    SAME_RECORDING,
    SAME_SONG,
    find_duplicate_groups,
)


def duplicate_track(
    path: str,
    title: str,
    artist: str,
    *,
    bpm: float | None = 105.02,
    duration: float | None = 153.0,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=artist,
        bpm=bpm,
        camelot_key="8A",
        energy_level=5,
        energy_in=5,
        energy_out=5,
        duration=duration,
        genre="House",
        tags=["Peak"],
        metadata_status="complete",
    )


def test_rule_a_groups_versions_of_the_same_song() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "Too Hot (Clean)", "Artist"),
        duplicate_track("/music/b.flac", "Too Hot (Single Version)", "Artist", duration=181.0),
    ]

    groups = find_duplicate_groups(tracks)

    assert len(groups) == 1
    assert groups[0].positions == (1, 2)
    assert groups[0].paths == ("/music/a.flac", "/music/b.flac")
    assert groups[0].reason == SAME_SONG


def test_rule_b_catches_repeat_with_damaged_title_metadata() -> None:
    # Real case: position 01 "9 To 5 [DJ Edit]" and position 02 "To 5 (DJ Edit)"
    # -- same Dolly Parton recording; the second copy lost the leading "9 " and
    # carries a different Camelot key, so exact title grouping cannot catch it.
    tracks = [
        duplicate_track("/music/9to5-edit.flac", "9 To 5 [DJ Edit]", "Dolly Parton", bpm=105.02),
        duplicate_track("/music/to5-edit.flac", "To 5 (DJ Edit)", "Dolly Parton", bpm=105.02),
    ]

    groups = find_duplicate_groups(tracks)

    assert len(groups) == 1
    assert groups[0].positions == (1, 2)
    assert groups[0].titles == ("9 To 5 [DJ Edit]", "To 5 (DJ Edit)")
    assert groups[0].reason == SAME_RECORDING


def test_half_time_bpm_notation_is_the_same_recording() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "Nightcall", "Artist", bpm=52.51),
        duplicate_track("/music/b.flac", "Nightcall Edit", "Artist", bpm=105.02),
    ]

    groups = find_duplicate_groups(tracks)

    assert len(groups) == 1
    assert groups[0].reason == SAME_RECORDING


def test_distinct_songs_by_same_artist_are_not_grouped() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "Song One", "Artist", bpm=120.0, duration=200.0),
        duplicate_track("/music/b.flac", "Different Life", "Artist", bpm=122.0, duration=210.0),
    ]

    assert find_duplicate_groups(tracks) == []


def test_same_artist_similar_songs_without_title_overlap_are_not_grouped() -> None:
    # Regression: synthetic test fixtures ("Electron test 1" vs "Electron test 2")
    # share artist, duration, and adjacent BPM within 0.5% but are different
    # songs -- rule B must not flag pairs whose normalized titles do not overlap.
    tracks = [
        duplicate_track("/music/a.flac", "Electron test 1", "XfinAudio Test", bpm=120.0, duration=2.0),
        duplicate_track("/music/b.flac", "Electron test 2", "XfinAudio Test", bpm=120.5, duration=2.0),
    ]

    assert find_duplicate_groups(tracks) == []


def test_truncated_title_of_same_recording_is_grouped() -> None:
    # Rule B's containment criterion: a damaged copy keeps the rest of the title
    # ("To 5" is contained in "9 To 5"), which no other rule can see.
    tracks = [
        duplicate_track("/music/a.flac", "Groove Is In The Heart", "Artist", bpm=120.0),
        duplicate_track("/music/b.flac", "Groove Is In", "Artist", bpm=120.0),
    ]

    groups = find_duplicate_groups(tracks)

    assert len(groups) == 1
    assert groups[0].reason == SAME_RECORDING


def test_duration_outside_tolerance_is_not_a_repeat() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "Song One", "Artist", duration=152.0),
        duplicate_track("/music/b.flac", "Song One Edit", "Artist", duration=154.1),
    ]

    assert find_duplicate_groups(tracks) == []


def test_bpm_outside_tolerance_is_not_a_repeat() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "Song One", "Artist", bpm=105.02),
        duplicate_track("/music/b.flac", "Song One Edit", "Artist", bpm=105.60),
    ]

    assert find_duplicate_groups(tracks) == []


def test_missing_bpm_or_duration_blocks_rule_b_only() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "Song One", "Artist", bpm=None),
        duplicate_track("/music/b.flac", "Song One Edit", "Artist"),
    ]

    assert find_duplicate_groups(tracks) == []

    tracks = [
        duplicate_track("/music/a.flac", "Song One", "Artist", duration=None),
        duplicate_track("/music/b.flac", "Song One Edit", "Artist"),
    ]

    assert find_duplicate_groups(tracks) == []


def test_blank_metadata_is_never_grouped() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "", "Artist"),
        duplicate_track("/music/b.flac", "Same Song", "Artist"),
    ]

    assert find_duplicate_groups(tracks) == []

    tracks = [
        duplicate_track("/music/a.flac", "Same Song", ""),
        duplicate_track("/music/b.flac", "Same Song", "Artist"),
    ]

    assert find_duplicate_groups(tracks) == []


def test_transitive_versions_form_one_group() -> None:
    tracks = [
        duplicate_track("/music/a.flac", "Too Hot (Clean)", "Artist"),
        duplicate_track("/music/b.flac", "Too Hot (Single Version)", "Artist"),
        duplicate_track("/music/c.flac", "Too Hot [DJ Edit]", "Artist"),
    ]

    groups = find_duplicate_groups(tracks)

    assert len(groups) == 1
    assert groups[0].positions == (1, 2, 3)


def test_groups_are_deterministic_and_sorted_by_first_position() -> None:
    tracks = [
        duplicate_track("/music/b1.flac", "Second Pair", "Artist", duration=150.0),
        duplicate_track("/music/a1.flac", "First Pair A", "Artist"),
        duplicate_track("/music/b2.flac", "Second Pair B", "Artist", duration=150.9),
        duplicate_track("/music/a2.flac", "First Pair A (Single Version)", "Artist"),
    ]

    groups = find_duplicate_groups(tracks)

    assert [(group.positions, group.reason) for group in groups] == [
        ((1, 3), SAME_RECORDING),
        ((2, 4), SAME_SONG),
    ]
