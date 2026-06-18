"""Tests for the genre-decision presentation helpers (PR6 Task 6.1).

The desktop UI uses these helpers to render the canonical (enriched) genre,
a confidence/low-confidence badge, and a sources tooltip. They are pure
(no Qt dependency) so they are testable without offscreen widgets.
"""

from __future__ import annotations

from xfinaudio.desktop.rendering import (
    format_genre_badge,
    format_genre_cell,
    format_genre_decision,
    format_genre_sources_tooltip,
)
from xfinaudio.genre.models import GenreCandidate, GenreDecision, GenreProvenance
from xfinaudio.library.models import TrackRecord


def _decision(
    primary: str | None,
    *,
    confidence: float = 0.9,
    low_confidence: bool = False,
    candidates: tuple[GenreCandidate, ...] = (),
    scores: dict[str, float] | None = None,
) -> GenreDecision:
    return GenreDecision(
        primary=primary,
        top_n=(primary,) if primary else (),
        confidence=confidence,
        low_confidence=low_confidence,
        provenance=GenreProvenance(
            candidates=candidates,
            source_trust={"discogs": 1.0, "musicbrainz_genres": 0.9, "musicbrainz_tags": 0.5},
            scores=scores or {},
        ),
    )


def _candidate(canonical: str, source: str, confidence: float) -> GenreCandidate:
    return GenreCandidate(
        canonical_genre=canonical,
        raw_label=canonical.lower(),
        source=source,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# format_genre_decision — the canonical (or raw) genre string
# ---------------------------------------------------------------------------


def test_format_genre_decision_returns_canonical_primary() -> None:
    track = TrackRecord(
        path="/lib/a.flac",
        genre="Electronica",  # misleading raw tag
        genre_decision=_decision("Tech House"),
    )

    assert format_genre_decision(track) == "Tech House"


def test_format_genre_decision_falls_back_to_raw_when_no_decision() -> None:
    track = TrackRecord(path="/lib/a.flac", genre="House")

    assert format_genre_decision(track) == "House"


def test_format_genre_decision_returns_empty_when_nothing_available() -> None:
    track = TrackRecord(path="/lib/a.flac")

    assert format_genre_decision(track) == ""


def test_format_genre_decision_falls_back_when_decision_has_no_primary() -> None:
    track = TrackRecord(
        path="/lib/a.flac",
        genre="House",
        genre_decision=_decision(primary=None),
    )

    assert format_genre_decision(track) == "House"


# ---------------------------------------------------------------------------
# format_genre_badge — confidence / low-confidence indicator
# ---------------------------------------------------------------------------


def test_format_genre_badge_is_empty_when_no_decision() -> None:
    track = TrackRecord(path="/lib/a.flac", genre="House")

    assert format_genre_badge(track) == ""


def test_format_genre_badge_signals_high_confidence() -> None:
    track = TrackRecord(
        path="/lib/a.flac",
        genre_decision=_decision("Techno", confidence=0.9),
    )

    badge = format_genre_badge(track)

    assert badge  # non-empty
    # The badge should hint at high confidence
    assert "0.9" in badge or "high" in badge.lower() or "✓" in badge or "🎯" in badge


def test_format_genre_badge_signals_low_confidence_when_flagged() -> None:
    track = TrackRecord(
        path="/lib/a.flac",
        genre_decision=_decision("Tech House", confidence=0.4, low_confidence=True),
    )

    badge = format_genre_badge(track)

    assert badge
    # Distinct from the high-confidence case
    assert "low" in badge.lower() or "❓" in badge or "!" in badge


def test_format_genre_badge_signals_low_confidence_when_below_threshold() -> None:
    track = TrackRecord(
        path="/lib/a.flac",
        genre_decision=_decision("Tech House", confidence=0.3),
    )

    badge = format_genre_badge(track)

    assert badge  # non-empty: low-confidence visual signal
    # Should not look like a high-confidence badge
    high_track = TrackRecord(
        path="/lib/b.flac",
        genre_decision=_decision("Tech House", confidence=0.9),
    )
    assert badge != format_genre_badge(high_track)


# ---------------------------------------------------------------------------
# format_genre_cell — combined cell content (canonical + badge)
# ---------------------------------------------------------------------------


def test_format_genre_cell_combines_canonical_and_badge() -> None:
    track = TrackRecord(
        path="/lib/a.flac",
        genre_decision=_decision("Tech House", confidence=0.9),
    )

    cell = format_genre_cell(track)

    assert "Tech House" in cell
    # Badge text appears in the cell
    assert format_genre_badge(track) in cell or format_genre_badge(track).strip() in cell


def test_format_genre_cell_handles_no_decision() -> None:
    track = TrackRecord(path="/lib/a.flac", genre="House")

    cell = format_genre_cell(track)

    assert "House" in cell
    assert format_genre_badge(track) == ""  # no badge for un-enriched


def test_format_genre_cell_handles_empty_track() -> None:
    track = TrackRecord(path="/lib/a.flac")

    assert format_genre_cell(track) == ""


# ---------------------------------------------------------------------------
# format_genre_sources_tooltip — multi-line explainability
# ---------------------------------------------------------------------------


def test_format_genre_sources_tooltip_lists_canonical_and_sources() -> None:
    candidates = (
        _candidate("Tech House", "discogs", 0.9),
        _candidate("Tech House", "musicbrainz_genres", 0.8),
        _candidate("Deep House", "musicbrainz_genres", 0.4),
    )
    track = TrackRecord(
        path="/lib/a.flac",
        genre_decision=_decision(
            "Tech House",
            confidence=0.85,
            candidates=candidates,
            scores={"Tech House": 1.62, "Deep House": 0.36},
        ),
    )

    tooltip = format_genre_sources_tooltip(track)

    # Tooltip names the canonical primary
    assert "Tech House" in tooltip
    # Lists the contributing sources
    assert "discogs" in tooltip
    assert "musicbrainz_genres" in tooltip
    # Multi-line
    assert "\n" in tooltip


def test_format_genre_sources_tooltip_empty_when_no_decision() -> None:
    track = TrackRecord(path="/lib/a.flac", genre="House")

    assert format_genre_sources_tooltip(track) == ""


def test_format_genre_sources_tooltip_marks_low_confidence() -> None:
    track = TrackRecord(
        path="/lib/a.flac",
        genre_decision=_decision("Tech House", confidence=0.4, low_confidence=True),
    )

    tooltip = format_genre_sources_tooltip(track)

    assert "low" in tooltip.lower() or "!" in tooltip


def test_format_genre_sources_tooltip_includes_top_n() -> None:
    candidates = (
        _candidate("Tech House", "discogs", 0.9),
        _candidate("Deep House", "musicbrainz_genres", 0.4),
    )
    decision = _decision(
        "Tech House",
        confidence=0.85,
        candidates=candidates,
        scores={"Tech House": 0.9, "Deep House": 0.4},
    )
    # Override top_n to include both
    decision = decision.model_copy(update={"top_n": ("Tech House", "Deep House")})

    track = TrackRecord(path="/lib/a.flac", genre_decision=decision)

    tooltip = format_genre_sources_tooltip(track)

    assert "Tech House" in tooltip
    assert "Deep House" in tooltip
