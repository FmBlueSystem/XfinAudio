"""Tests for the effective_genre precedence helper (PR5 Task 5.4).

The helper centralizes the canonical-vs-raw genre precedence used by
recommendation, library_health, and scoring.
"""

from __future__ import annotations

from xfinaudio.genre.effective_genre import effective_genre
from xfinaudio.genre.models import GenreDecision, GenreProvenance
from xfinaudio.library.models import TrackRecord


def test_effective_genre_prefers_canonical_when_present() -> None:
    track = TrackRecord(
        path="/x/y.mp3",
        genre="Electronica",  # file tag
        genre_decision=GenreDecision(
            primary="Tech House",
            top_n=("Tech House",),
            confidence=0.9,
            low_confidence=False,
            provenance=GenreProvenance(),
        ),
    )

    assert effective_genre(track) == "Tech House"


def test_effective_genre_falls_back_to_file_tag() -> None:
    track = TrackRecord(path="/x/y.mp3", genre="House")

    assert effective_genre(track) == "House"


def test_effective_genre_returns_none_when_neither() -> None:
    track = TrackRecord(path="/x/y.mp3")

    assert effective_genre(track) is None


def test_effective_genre_falls_back_when_decision_has_no_primary() -> None:
    track = TrackRecord(
        path="/x/y.mp3",
        genre="House",
        genre_decision=GenreDecision(
            primary=None,
            top_n=(),
            confidence=0.0,
            low_confidence=True,
            provenance=GenreProvenance(),
        ),
    )

    assert effective_genre(track) == "House"
