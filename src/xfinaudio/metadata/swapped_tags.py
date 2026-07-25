"""Detect tracks whose title and artist tags were written the wrong way round.

Some releases ship with the two fields transposed -- a real 10,392-track library
had 18 of them, e.g. ``title="Queen"`` / ``artist="Another One Bites The Dust"``.
The parser reads those files correctly; the tags themselves are wrong.

The library is its own reference: a title that appears as an *artist* on other
tracks is the signal. Ambiguous rows, where both sides look like artist names,
are deliberately not reported -- they need a human who knows the music.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from xfinaudio.library.models import TrackRecord

# How many other tracks must credit the suspect title as their artist before it
# counts as evidence. Two keeps single typos from being read as a pattern.
_MIN_ARTIST_OCCURRENCES = 2
# Above this, the current artist looks like a real artist too, so the row is
# ambiguous rather than swapped.
_MAX_OCCURRENCES_FOR_SUSPECT_ARTIST = 1


class SwapCandidate(BaseModel):
    """A track whose title and artist look transposed, with the evidence for it."""

    model_config = ConfigDict(frozen=True)

    path: str
    current_title: str
    current_artist: str
    suggested_title: str
    suggested_artist: str
    artist_occurrences: int


def _normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def find_swapped_title_artist(
    records: Iterable[TrackRecord],
    *,
    min_artist_occurrences: int = _MIN_ARTIST_OCCURRENCES,
) -> list[SwapCandidate]:
    """Return likely title/artist swaps, strongest evidence first.

    A row is reported when its title is credited as the artist on at least
    ``min_artist_occurrences`` other tracks, while its own artist value is
    almost never used as an artist elsewhere.

    The result is a shortlist for review, not a verdict: the heuristic cannot
    tell a swap from a track genuinely named after a band.
    """
    tracks = [record for record in records if record.title and record.artist]
    artist_counts = Counter(_normalize(record.artist) for record in tracks)

    candidates = [
        SwapCandidate(
            path=record.path,
            current_title=record.title or "",
            current_artist=record.artist or "",
            suggested_title=record.artist or "",
            suggested_artist=record.title or "",
            artist_occurrences=artist_counts[_normalize(record.title)],
        )
        for record in tracks
        if _normalize(record.title) != _normalize(record.artist)
        and artist_counts[_normalize(record.title)] >= min_artist_occurrences
        and artist_counts[_normalize(record.artist)] <= _MAX_OCCURRENCES_FOR_SUSPECT_ARTIST
    ]
    return sorted(candidates, key=lambda candidate: (-candidate.artist_occurrences, candidate.path))


__all__ = ["SwapCandidate", "find_swapped_title_artist"]
