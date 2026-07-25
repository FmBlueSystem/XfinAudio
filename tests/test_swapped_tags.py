"""Tests for detecting tracks whose title and artist tags are swapped."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.swapped_tags import find_swapped_title_artist


def track(path: str, *, title: str, artist: str) -> TrackRecord:
    return TrackRecord(path=path, title=title, artist=artist, metadata_status="complete")


def test_detects_track_whose_title_is_a_known_artist() -> None:
    """A title that the rest of the library uses as an artist name is the signal."""
    records = [
        track("/queen-swapped.flac", title="Queen", artist="Another One Bites The Dust"),
        track("/b.flac", title="Bohemian Rhapsody", artist="Queen"),
        track("/c.flac", title="We Will Rock You", artist="Queen"),
    ]

    candidates = find_swapped_title_artist(records)

    assert [candidate.path for candidate in candidates] == ["/queen-swapped.flac"]
    assert candidates[0].suggested_title == "Another One Bites The Dust"
    assert candidates[0].suggested_artist == "Queen"
    assert candidates[0].artist_occurrences == 2


def test_ignores_row_whose_current_artist_is_also_a_known_artist() -> None:
    """Both sides looking like artists is ambiguous, so it is left for a human.

    Real case from a 10,392-track library: "Poison" / "Block & Crown" is a real
    house track, not a swap.
    """
    records = [
        track("/ambiguous.flac", title="Poison", artist="Block & Crown"),
        track("/b.flac", title="Anthem", artist="Block & Crown"),
        track("/c.flac", title="Nightfall", artist="Poison"),
        track("/d.flac", title="Fallen Angel", artist="Poison"),
    ]

    candidates = find_swapped_title_artist(records)

    assert candidates == []


def test_ignores_correctly_tagged_library() -> None:
    records = [
        track("/a.flac", title="Bohemian Rhapsody", artist="Queen"),
        track("/b.flac", title="We Will Rock You", artist="Queen"),
        track("/c.flac", title="Girls Just Wanna Have Fun", artist="Cyndi Lauper"),
    ]

    assert find_swapped_title_artist(records) == []


def test_ignores_rows_missing_either_field() -> None:
    records = [
        TrackRecord(path="/a.flac", title="Queen", artist=None, metadata_status="incomplete"),
        TrackRecord(path="/b.flac", title=None, artist="Queen", metadata_status="incomplete"),
        track("/c.flac", title="Killer Queen", artist="Queen"),
        track("/d.flac", title="Somebody To Love", artist="Queen"),
    ]

    assert find_swapped_title_artist(records) == []


def test_ranks_candidates_by_strength_of_evidence() -> None:
    """Reviewers should see the most confident swaps first."""
    records = [
        track("/weak.flac", title="Becca", artist="You Make Me Feel"),
        track("/strong.flac", title="Donna Summer", artist="Love Is In Control"),
        track("/b.flac", title="Bad Girls", artist="Donna Summer"),
        track("/c.flac", title="Hot Stuff", artist="Donna Summer"),
        track("/d.flac", title="On The Radio", artist="Donna Summer"),
        track("/e.flac", title="Sway", artist="Becca"),
        track("/f.flac", title="Alive", artist="Becca"),
    ]

    candidates = find_swapped_title_artist(records)

    assert [candidate.path for candidate in candidates] == ["/strong.flac", "/weak.flac"]


def test_comparison_ignores_case_and_surrounding_whitespace() -> None:
    records = [
        track("/swapped.flac", title="  queen ", artist="Another One Bites The Dust"),
        track("/b.flac", title="Bohemian Rhapsody", artist="Queen"),
        track("/c.flac", title="We Will Rock You", artist="QUEEN"),
    ]

    candidates = find_swapped_title_artist(records)

    assert [candidate.path for candidate in candidates] == ["/swapped.flac"]
