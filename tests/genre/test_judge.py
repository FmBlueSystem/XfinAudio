"""Tests for the deterministic weighted-vote consensus judge (PR5 Task 5.1).

Covers spec Requirement 5 Scenarios 5.1-5.5.
"""

from __future__ import annotations

from xfinaudio.genre.judge import decide
from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.settings import GenreEnrichmentSettings


def _settings(
    *,
    enabled: bool = True,
    providers: dict[str, bool] | None = None,
    source_trust: dict[str, float] | None = None,
    min_score_threshold: float = 0.0,
    margin_threshold: float = 0.15,
    low_confidence_floor: float = 0.0,
    llm_tiebreaker_enabled: bool = False,
) -> GenreEnrichmentSettings:
    return GenreEnrichmentSettings(
        enabled=enabled,
        providers=providers
        if providers is not None
        else {"discogs": True, "musicbrainz_genres": True, "musicbrainz_tags": True},
        source_trust=source_trust
        if source_trust is not None
        else {"discogs": 1.0, "musicbrainz_genres": 0.9, "musicbrainz_tags": 0.5},
        min_score_threshold=min_score_threshold,
        margin_threshold=margin_threshold,
        low_confidence_floor=low_confidence_floor,
        llm_tiebreaker_enabled=llm_tiebreaker_enabled,
    )


def _cand(canonical: str, source: str, confidence: float = 1.0) -> GenreCandidate:
    return GenreCandidate(
        canonical_genre=canonical,
        raw_label=canonical.lower(),
        source=source,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Scenario 5.1 — Agreement reinforces a single genre
# ---------------------------------------------------------------------------


def test_judge_agreement_reinforces_confidence() -> None:
    """Multiple sources agreeing raise confidence over a single conflicted source."""
    settings = _settings()
    # A single source that votes for two different genres has low confidence
    # because there is no corroboration; the primary only wins by the trust prior.
    single = [
        _cand("Techno", "discogs", 0.8),
        _cand("House", "discogs", 0.5),
    ]
    # Two sources agreeing on the same genre concentrate all mass on it.
    agreed = [
        _cand("Techno", "discogs", 0.8),
        _cand("Techno", "musicbrainz_genres", 0.8),
    ]

    decision_single = decide(single, settings)
    decision_agreed = decide(agreed, settings)

    assert decision_agreed.primary == "Techno"
    assert decision_single.primary == "Techno"
    assert decision_agreed.confidence > decision_single.confidence


# ---------------------------------------------------------------------------
# Scenario 5.2 — Conflict resolved by weighted vote
# ---------------------------------------------------------------------------


def test_judge_conflict_resolved_by_weighted_vote() -> None:
    settings = _settings()
    candidates = [
        _cand("Tech House", "discogs", 1.0),  # score: 1.0 * 1.0 = 1.0
        _cand("House", "musicbrainz_genres", 1.0),  # score: 0.9 * 1.0 = 0.9
    ]

    decision = decide(candidates, settings)

    assert decision.primary == "Tech House"
    assert "Tech House" in decision.provenance.scores
    assert "House" in decision.provenance.scores
    assert decision.provenance.scores["Tech House"] > decision.provenance.scores["House"]


# ---------------------------------------------------------------------------
# Scenario 5.3 — Low confidence flag on thin margin
# ---------------------------------------------------------------------------


def test_judge_marks_low_confidence_on_thin_margin() -> None:
    settings = _settings(margin_threshold=0.2)  # 0.1 margin < 0.2
    candidates = [
        _cand("Tech House", "discogs", 1.0),  # 1.0
        _cand("House", "musicbrainz_genres", 1.0),  # 0.9; margin = 0.1
    ]

    decision = decide(candidates, settings)

    assert decision.low_confidence is True
    assert "Tech House" in decision.top_n
    assert "House" in decision.top_n


def test_judge_marks_low_confidence_when_total_mass_below_floor() -> None:
    settings = _settings(low_confidence_floor=0.6)  # total score 0.5 < 0.6
    candidates = [_cand("Techno", "musicbrainz_tags", 1.0)]  # 0.5 * 1.0 = 0.5

    decision = decide(candidates, settings)

    assert decision.low_confidence is True
    assert decision.primary == "Techno"


# ---------------------------------------------------------------------------
# Scenario 5.4 — Determinism
# ---------------------------------------------------------------------------


def test_judge_is_deterministic() -> None:
    settings = _settings()
    candidates = [
        _cand("Tech House", "discogs", 1.0),
        _cand("House", "musicbrainz_genres", 1.0),
        _cand("Deep House", "musicbrainz_tags", 0.5),
    ]

    first = decide(candidates, settings)
    second = decide(candidates, settings)
    third = decide(list(candidates), settings)  # also via list

    assert first == second
    assert first == third
    assert first.top_n == second.top_n
    assert first.confidence == second.confidence


def test_judge_tie_breaks_alphabetically() -> None:
    """Equal scores are broken by canonical name for determinism."""
    settings = _settings(margin_threshold=0.0)
    candidates = [
        _cand("Techno", "discogs", 1.0),  # score 1.0
        _cand("House", "musicbrainz_genres", 1.0),  # score 0.9
        _cand("Ambient", "musicbrainz_tags", 1.0),  # score 0.5
    ]

    decision = decide(candidates, settings)

    # Primary is the highest score.
    assert decision.top_n[0] == "Techno"
    # top_n is the deterministic ranking by (-score, canonical_name): Techno, House, Ambient.
    assert decision.top_n == ("Techno", "House", "Ambient")


# ---------------------------------------------------------------------------
# Scenario 5.5 — Empty input
# ---------------------------------------------------------------------------


def test_judge_returns_empty_decision_when_no_candidates() -> None:
    settings = _settings()
    decision = decide([], settings)

    assert decision.primary is None
    assert decision.top_n == ()
    assert decision.confidence == 0.0
    assert decision.low_confidence is True


def test_judge_skips_unmapped_candidates() -> None:
    from xfinaudio.genre.normalizer import UNMAPPED

    settings = _settings()
    candidates = [
        GenreCandidate(
            canonical_genre=UNMAPPED,
            raw_label="qwerty noise",
            source="discogs",
            confidence=1.0,
        ),
        _cand("Techno", "musicbrainz_genres", 1.0),
    ]

    decision = decide(candidates, settings)

    assert decision.primary == "Techno"
    # UNMAPPED is recorded in provenance.candidates but not in scores
    assert "Techno" in decision.provenance.scores
    assert UNMAPPED not in decision.provenance.scores


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_judge_provenance_records_all_candidates_and_trust() -> None:
    settings = _settings()
    candidates = [_cand("Techno", "discogs", 0.9)]

    decision = decide(candidates, settings)

    assert decision.provenance.candidates == tuple(candidates)
    assert decision.provenance.source_trust == settings.source_trust
    assert "Techno" in decision.provenance.scores
