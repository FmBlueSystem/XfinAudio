"""Integration tests for genre enrichment wiring (PR5 Task 5.4).

Covers spec Requirement 7 Scenarios 7.1 (recommendation uses canonical genre)
and 7.2 (library health variant detection prefers canonical).
"""

from __future__ import annotations

from xfinaudio.genre.models import GenreCandidate, GenreDecision, GenreProvenance
from xfinaudio.library.library_health import analyze_library_health
from xfinaudio.library.models import TrackRecord


def _decision(primary: str) -> GenreDecision:
    return GenreDecision(
        primary=primary,
        top_n=(primary,),
        confidence=0.9,
        low_confidence=False,
        provenance=GenreProvenance(
            candidates=(
                GenreCandidate(
                    canonical_genre=primary,
                    raw_label=primary.lower(),
                    source="discogs",
                    confidence=0.9,
                ),
            ),
            source_trust={"discogs": 1.0},
            scores={primary: 0.9},
        ),
    )


# ---------------------------------------------------------------------------
# Scenario 7.2: library_health variant detection prefers canonical genre
# ---------------------------------------------------------------------------


def test_health_collapses_canonical_genre_variants() -> None:
    """Two raw spellings that map to the same canonical genre should not
    be reported as a variant group once the decision is attached."""
    tracks = [
        TrackRecord(
            path="/lib/a.flac",
            genre="tech house",
            genre_decision=_decision("Tech House"),
        ),
        TrackRecord(
            path="/lib/b.flac",
            genre="Tech-House",
            genre_decision=_decision("Tech House"),
        ),
        TrackRecord(
            path="/lib/c.flac",
            genre="TECH HOUSE",
            genre_decision=_decision("Tech House"),
        ),
    ]

    report = analyze_library_health(tracks)

    # All three map to the canonical "Tech House"; no variant group.
    assert report.genre_variant_groups == 0


def test_health_falls_back_to_raw_genre_when_no_decision() -> None:
    """Tracks without a decision still get their raw genre analyzed."""
    tracks = [
        TrackRecord(path="/lib/a.flac", genre="tech house"),
        TrackRecord(path="/lib/b.flac", genre="Tech House"),
    ]

    report = analyze_library_health(tracks)

    # Without a decision, the two raw spellings count as one variant group.
    assert report.genre_variant_groups == 1


def test_health_mixed_decision_and_no_decision_uses_effective_genre() -> None:
    tracks = [
        TrackRecord(path="/lib/a.flac", genre="tech house", genre_decision=_decision("Tech House")),
        TrackRecord(path="/lib/b.flac", genre="Tech House"),  # no decision
    ]

    report = analyze_library_health(tracks)

    # effective_genre("tech house" + decision) = "Tech House" == effective_genre("Tech House")
    assert report.genre_variant_groups == 0
