"""Tests for the genre enrichment Pydantic models (PR2, Task 2.1).

Covers spec Requirement 2 models (Requirements 5 & 6 behavior is exercised
in PR5 tests; this file only asserts the model invariants).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from xfinaudio.genre.models import GenreCandidate, GenreDecision, GenreProvenance


def test_genre_candidate_requires_confidence_in_range() -> None:
    with pytest.raises(ValidationError):
        GenreCandidate(
            canonical_genre="Tech House",
            raw_label="tech house",
            source="discogs",
            confidence=1.5,
        )
    with pytest.raises(ValidationError):
        GenreCandidate(
            canonical_genre="Tech House",
            raw_label="tech house",
            source="discogs",
            confidence=-0.1,
        )


def test_genre_candidate_is_frozen() -> None:
    candidate = GenreCandidate(
        canonical_genre="Tech House",
        raw_label="tech house",
        source="discogs",
        confidence=0.9,
    )

    with pytest.raises(ValidationError):
        candidate.confidence = 0.5  # type: ignore[misc]


def test_genre_provenance_records_candidates_and_trust() -> None:
    candidate = GenreCandidate(
        canonical_genre="Tech House",
        raw_label="tech house",
        source="discogs",
        confidence=0.9,
    )
    provenance = GenreProvenance(
        candidates=(candidate,),
        source_trust={"discogs_styles": 1.0},
        scores={"Tech House": 0.9},
    )

    assert provenance.candidates == (candidate,)
    assert provenance.source_trust == {"discogs_styles": 1.0}
    assert provenance.scores == {"Tech House": 0.9}


def test_genre_decision_top_n_preserves_order() -> None:
    candidate = GenreCandidate(
        canonical_genre="Tech House",
        raw_label="tech house",
        source="discogs",
        confidence=0.9,
    )
    provenance = GenreProvenance(
        candidates=(candidate,),
        source_trust={"discogs_styles": 1.0},
        scores={"Tech House": 0.9, "House": 0.4},
    )
    decision = GenreDecision(
        primary="Tech House",
        top_n=("Tech House", "House"),
        confidence=0.9,
        low_confidence=False,
        provenance=provenance,
    )

    assert decision.top_n[0] == "Tech House"
    assert decision.confidence == 0.9
    assert decision.provenance is provenance


def test_genre_decision_allows_no_signal() -> None:
    provenance = GenreProvenance(candidates=(), source_trust={}, scores={})
    decision = GenreDecision(
        primary=None,
        top_n=(),
        confidence=0.0,
        low_confidence=True,
        provenance=provenance,
    )

    assert decision.primary is None
    assert decision.top_n == ()
    assert decision.low_confidence is True


def test_genre_decision_is_frozen() -> None:
    candidate = GenreCandidate(
        canonical_genre="Tech House",
        raw_label="tech house",
        source="discogs",
        confidence=0.9,
    )
    provenance = GenreProvenance(
        candidates=(candidate,),
        source_trust={"discogs_styles": 1.0},
        scores={"Tech House": 0.9},
    )
    decision = GenreDecision(
        primary="Tech House",
        top_n=("Tech House",),
        confidence=0.9,
        low_confidence=False,
        provenance=provenance,
    )

    with pytest.raises(ValidationError):
        decision.primary = "House"  # type: ignore[misc]
