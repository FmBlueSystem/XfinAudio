"""Tests for the local LLM tie-breaker (PR6).

Covers spec Requirement 6 Scenarios 6.1-6.4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xfinaudio.genre.judge import decide
from xfinaudio.genre.llm_judge import LocalLlmTieBreaker
from xfinaudio.genre.models import GenreCandidate, GenreDecision, GenreProvenance
from xfinaudio.genre.settings import (
    DEFAULT_LLM_TIEBREAKER_MODEL,
    DEFAULT_LLM_TIEBREAKER_URL,
    GenreEnrichmentSettings,
)


def _settings(
    *,
    enabled: bool = False,
    margin_threshold: float = 0.15,
    source_trust: dict[str, float] | None = None,
) -> GenreEnrichmentSettings:
    return GenreEnrichmentSettings(
        enabled=True,
        providers={"discogs": True, "musicbrainz_genres": True},
        source_trust=source_trust or {"discogs": 1.0, "musicbrainz_genres": 0.9},
        margin_threshold=margin_threshold,
        low_confidence_floor=0.0,
        llm_tiebreaker_enabled=enabled,
        llm_tiebreaker_url=DEFAULT_LLM_TIEBREAKER_URL,
        llm_tiebreaker_model=DEFAULT_LLM_TIEBREAKER_MODEL,
    )


def _cand(canonical: str, source: str, confidence: float = 1.0) -> GenreCandidate:
    return GenreCandidate(
        canonical_genre=canonical,
        raw_label=canonical.lower(),
        source=source,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# LocalLlmTieBreaker
# ---------------------------------------------------------------------------


def test_tiebreaker_returns_chosen_candidate_from_top_n() -> None:
    """The model is asked to pick; its response is mapped to a top_n entry."""

    def fetcher(prompt: str) -> dict[str, Any]:
        return {"response": "Tech House"}

    tb = LocalLlmTieBreaker(fetcher=fetcher)
    chosen = tb.break_tie(
        decision=GenreDecision(
            primary="Tech House",
            top_n=("Tech House", "Deep House"),
            confidence=0.5,
            low_confidence=True,
            provenance=GenreProvenance(),
        ),
    )
    assert chosen == "Tech House"


def test_tiebreaker_rejects_response_outside_top_n() -> None:
    def fetcher(prompt: str) -> dict[str, Any]:
        return {"response": "Bogus Genre"}  # not in top_n

    tb = LocalLlmTieBreaker(fetcher=fetcher)
    chosen = tb.break_tie(
        decision=GenreDecision(
            primary="Tech House",
            top_n=("Tech House", "Deep House"),
            confidence=0.5,
            low_confidence=True,
            provenance=GenreProvenance(),
        ),
    )
    assert chosen is None


def test_tiebreaker_caches_responses_per_top_n() -> None:
    calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        calls.append(prompt)
        return {"response": "Tech House"}

    tb = LocalLlmTieBreaker(fetcher=fetcher)
    decision = GenreDecision(
        primary="Tech House",
        top_n=("Tech House", "Deep House"),
        confidence=0.5,
        low_confidence=True,
        provenance=GenreProvenance(),
    )
    tb.break_tie(decision=decision)
    tb.break_tie(decision=decision)
    tb.break_tie(decision=decision)
    assert len(calls) == 1  # cached after first call


def test_tiebreaker_cache_differentiates_by_top_n_order() -> None:
    """Reordered top_n should trigger a fresh model call (order matters for cache key)."""
    calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        calls.append(prompt)
        return {"response": "Deep House"}

    tb = LocalLlmTieBreaker(fetcher=fetcher)
    base = GenreDecision(
        primary="Tech House",
        top_n=("Tech House", "Deep House"),
        confidence=0.5,
        low_confidence=True,
        provenance=GenreProvenance(),
    )
    tb.break_tie(decision=base)
    reversed_decision = base.model_copy(update={"top_n": ("Deep House", "Tech House")})
    tb.break_tie(decision=reversed_decision)
    assert len(calls) == 2


def test_tiebreaker_handles_malformed_response_gracefully() -> None:
    def fetcher(prompt: str) -> dict[str, Any]:
        return {"response": None}  # malformed

    tb = LocalLlmTieBreaker(fetcher=fetcher)
    chosen = tb.break_tie(
        decision=GenreDecision(
            primary="Tech House",
            top_n=("Tech House",),
            confidence=0.5,
            low_confidence=True,
            provenance=GenreProvenance(),
        )
    )
    assert chosen is None


def test_tiebreaker_handles_fetcher_exception() -> None:
    def bad_fetcher(prompt: str) -> dict[str, Any]:
        raise RuntimeError("ollama down")

    tb = LocalLlmTieBreaker(fetcher=bad_fetcher)
    chosen = tb.break_tie(
        decision=GenreDecision(
            primary="Tech House",
            top_n=("Tech House",),
            confidence=0.5,
            low_confidence=True,
            provenance=GenreProvenance(),
        )
    )
    assert chosen is None


def test_tiebreaker_persists_cache_to_disk(tmp_path: Path) -> None:
    calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        calls.append(prompt)
        return {"response": "Tech House"}

    cache = tmp_path / "llm_cache.sqlite"
    decision = GenreDecision(
        primary="Tech House",
        top_n=("Tech House", "Deep House"),
        confidence=0.5,
        low_confidence=True,
        provenance=GenreProvenance(),
    )

    # First instance populates the disk cache.
    LocalLlmTieBreaker(fetcher=fetcher, cache_path=cache).break_tie(decision=decision)
    # Second instance with no fetcher: must serve from disk.
    second = LocalLlmTieBreaker(cache_path=cache)
    chosen = second.break_tie(decision=decision)
    assert chosen == "Tech House"


def test_tiebreaker_prompt_includes_all_top_n_candidates() -> None:
    captured: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        captured.append(prompt)
        return {"response": "Tech House"}

    tb = LocalLlmTieBreaker(fetcher=fetcher)
    tb.break_tie(
        decision=GenreDecision(
            primary="Tech House",
            top_n=("Tech House", "Deep House", "House"),
            confidence=0.5,
            low_confidence=True,
            provenance=GenreProvenance(),
        )
    )
    assert "Tech House" in captured[0]
    assert "Deep House" in captured[0]
    assert "House" in captured[0]


# ---------------------------------------------------------------------------
# decide() integration
# ---------------------------------------------------------------------------


def test_judge_does_not_invoke_llm_when_disabled() -> None:
    """Even on a low_confidence decision, the LLM is off by default."""
    settings = _settings(enabled=False, margin_threshold=0.2)
    candidates = [
        _cand("Tech House", "discogs", 1.0),  # 1.0
        _cand("House", "musicbrainz_genres", 1.0),  # 0.9, margin 0.1
    ]
    decision = decide(candidates, settings)
    assert decision.low_confidence is True
    # primary is the deterministic argmax; LLM is not invoked
    assert decision.primary == "Tech House"


def test_judge_does_not_modify_decision_when_llm_returns_none() -> None:
    """If the LLM tie-breaker is enabled but returns None (failure/invalid),
    the deterministic decision stands."""
    from xfinaudio.genre.judge import decide_with_llm

    def bad_fetcher(prompt: str) -> dict[str, Any]:
        return {"response": "Wrong Answer"}

    settings = _settings(enabled=True, margin_threshold=0.2)
    candidates = [
        _cand("Tech House", "discogs", 1.0),
        _cand("House", "musicbrainz_genres", 1.0),
    ]
    base = decide(candidates, settings)
    tb = LocalLlmTieBreaker(fetcher=bad_fetcher)
    decided = decide_with_llm(base, tb)
    assert decided.primary == "Tech House"
    assert decided.low_confidence is True


def test_judge_overrides_primary_when_llm_picks() -> None:
    """The LLM tie-breaker can override the deterministic primary when its
    choice is one of the top_n candidates."""
    from xfinaudio.genre.judge import decide_with_llm

    def fetcher(prompt: str) -> dict[str, Any]:
        return {"response": "House"}  # model picks the runner-up

    settings = _settings(enabled=True, margin_threshold=0.2)
    candidates = [
        _cand("Tech House", "discogs", 1.0),
        _cand("House", "musicbrainz_genres", 1.0),
    ]
    base = decide(candidates, settings)
    tb = LocalLlmTieBreaker(fetcher=fetcher)
    decided = decide_with_llm(base, tb)
    assert decided.primary == "House"
    # Once the LLM picks, low_confidence is cleared (we have a decisive pick)
    assert decided.low_confidence is False


def test_judge_skips_llm_when_top_n_is_empty() -> None:
    from xfinaudio.genre.judge import decide_with_llm

    fetcher_calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        fetcher_calls.append(prompt)
        return {"response": "Tech House"}

    base = GenreDecision(
        primary=None,
        top_n=(),
        confidence=0.0,
        low_confidence=True,
        provenance=GenreProvenance(),
    )
    tb = LocalLlmTieBreaker(fetcher=fetcher)
    decided = decide_with_llm(base, tb)
    assert decided is base
    assert fetcher_calls == []  # no call made
