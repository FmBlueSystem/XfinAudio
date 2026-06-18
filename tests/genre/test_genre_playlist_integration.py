"""Integration tests for the same_genre strategy using effective_genre (PR5 Task 5.4).

Covers spec Requirement 7 Scenario 7.1 (same_genre uses canonical genre when
present, falling back to raw file tag when not).
"""

from __future__ import annotations

from xfinaudio.genre.models import GenreDecision, GenreProvenance
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import _apply_genre_filter


def _decision(primary: str) -> GenreDecision:
    return GenreDecision(
        primary=primary,
        top_n=(primary,),
        confidence=0.9,
        low_confidence=False,
        provenance=GenreProvenance(),
    )


def test_same_genre_filter_uses_canonical_genre() -> None:
    """The same_genre strategy should match tracks by canonical (enriched) genre."""
    tech_house_anchor = TrackRecord(
        path="/lib/a.flac",
        title="Track A",
        genre="Electronica",  # raw tag, misleading
        genre_decision=_decision("Tech House"),
    )
    deep_house = TrackRecord(
        path="/lib/b.flac",
        title="Track B",
        genre="House",
        genre_decision=_decision("Deep House"),
    )
    another_tech_house = TrackRecord(
        path="/lib/c.flac",
        title="Track C",
        genre="Disco",  # raw tag, different from canonical
        genre_decision=_decision("Tech House"),
    )
    tracks = [tech_house_anchor, deep_house, another_tech_house]
    controls = DJControls(start_path=tech_house_anchor.path)

    filtered, warnings = _apply_genre_filter(tracks, controls, preserve_paths={tech_house_anchor.path})

    paths = {t.path for t in filtered}
    # Anchor preserved; matching canonical also kept; non-matching deep house excluded.
    assert tech_house_anchor.path in paths
    assert another_tech_house.path in paths
    assert deep_house.path not in paths
    # Warning names the anchor's canonical genre.
    assert any("tech house" in w.lower() for w in warnings)


def test_same_genre_filter_falls_back_to_raw_when_no_decision() -> None:
    """When neither anchor nor candidate has a decision, the raw genre is used."""
    anchor = TrackRecord(path="/lib/a.flac", title="A", genre="Tech House")
    same_raw = TrackRecord(path="/lib/b.flac", title="B", genre="TECH HOUSE")  # casefold matches
    different = TrackRecord(path="/lib/c.flac", title="C", genre="Disco")
    tracks = [anchor, same_raw, different]
    controls = DJControls(start_path=anchor.path)

    filtered, _ = _apply_genre_filter(tracks, controls, preserve_paths={anchor.path})

    paths = {t.path for t in filtered}
    assert anchor.path in paths
    assert same_raw.path in paths
    assert different.path not in paths


def test_same_genre_filter_prefers_canonical_over_raw_for_anchor() -> None:
    """If the anchor has a decision, the decision's primary anchors the filter."""
    anchor = TrackRecord(
        path="/lib/a.flac",
        title="A",
        genre="Electronica",  # misleading raw tag
        genre_decision=_decision("Tech House"),
    )
    same_canonical = TrackRecord(
        path="/lib/b.flac",
        title="B",
        genre="Electronica",
        genre_decision=_decision("Tech House"),
    )
    same_raw_but_no_decision = TrackRecord(
        path="/lib/c.flac",
        title="C",
        genre="Electronica",  # would match the raw genre but is wrong
    )
    tracks = [anchor, same_canonical, same_raw_but_no_decision]
    controls = DJControls(start_path=anchor.path)

    filtered, _ = _apply_genre_filter(tracks, controls, preserve_paths={anchor.path})

    paths = {t.path for t in filtered}
    # The decision's canonical primary is "Tech House", so only canonical-Tech-House is kept.
    assert anchor.path in paths
    assert same_canonical.path in paths
    assert same_raw_but_no_decision.path not in paths
