"""Tests for the enrichment service (PR5 Task 5.2).

Covers spec Requirement 2 Scenario 2.3 (provider failure isolation),
general enrichment orchestration behavior, and the LLM tie-breaker
wiring (opt-in, default OFF, never invoked unless enabled).
"""

from __future__ import annotations

from typing import Any

from xfinaudio.genre.enrichment_service import EnrichmentService
from xfinaudio.genre.llm_judge import LocalLlmTieBreaker
from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.settings import GenreEnrichmentSettings


class _FakeProvider:
    def __init__(
        self,
        name: str,
        candidates: list[GenreCandidate],
        *,
        raises: bool = False,
    ) -> None:
        self.name = name
        self._candidates = candidates
        self._raises = raises
        self.calls = 0

    def fetch(self, track: object) -> list[GenreCandidate]:
        self.calls += 1
        if self._raises:
            raise RuntimeError("provider failed")
        return list(self._candidates)


def _cand(genre: str, source: str, confidence: float = 0.9) -> GenreCandidate:
    return GenreCandidate(
        canonical_genre=genre,
        raw_label=genre.lower(),
        source=source,
        confidence=confidence,
    )


def _track() -> Any:
    return type("_T", (), {"artist": "A", "title": "T"})()


def test_enrichment_service_returns_empty_decision_when_disabled() -> None:
    provider = _FakeProvider("a", [_cand("Techno", "a")])
    service = EnrichmentService(
        providers=[provider],
        settings=GenreEnrichmentSettings(enabled=False, providers={"a": True}),
    )

    decision = service.enrich(_track())

    assert decision.primary is None
    assert provider.calls == 0  # providers not queried


def test_enrichment_service_aggregates_candidates_from_all_providers() -> None:
    p1 = _FakeProvider("a", [_cand("Techno", "a", 0.8)])
    p2 = _FakeProvider("b", [_cand("Techno", "b", 0.7)])
    service = EnrichmentService(
        providers=[p1, p2],
        settings=GenreEnrichmentSettings(enabled=True, providers={"a": True, "b": True}),
    )

    decision = service.enrich(_track())

    assert decision.primary == "Techno"
    assert p1.calls == 1
    assert p2.calls == 1


def test_enrichment_service_isolates_failing_provider() -> None:
    good = _FakeProvider("good", [_cand("Techno", "good", 0.9)])
    bad = _FakeProvider("bad", [], raises=True)
    service = EnrichmentService(
        providers=[good, bad],
        settings=GenreEnrichmentSettings(enabled=True, providers={"good": True, "bad": True}),
    )

    decision = service.enrich(_track())

    assert decision.primary == "Techno"
    assert good.calls == 1
    # bad raised; must not propagate
    assert "good" in [c.source for c in decision.provenance.candidates]


def test_enrichment_service_continues_after_multiple_failures() -> None:
    bad1 = _FakeProvider("bad1", [], raises=True)
    bad2 = _FakeProvider("bad2", [], raises=True)
    good = _FakeProvider("good", [_cand("House", "good", 0.9)])
    service = EnrichmentService(
        providers=[bad1, bad2, good],
        settings=GenreEnrichmentSettings(enabled=True, providers={"bad1": True, "bad2": True, "good": True}),
    )

    decision = service.enrich(_track())

    assert decision.primary == "House"


def test_enrichment_service_with_no_providers_returns_empty() -> None:
    service = EnrichmentService(
        providers=[],
        settings=GenreEnrichmentSettings(enabled=True),
    )

    decision = service.enrich(_track())

    assert decision.primary is None
    assert decision.low_confidence is True


def test_enrichment_service_passes_settings_to_judge() -> None:
    """Custom judge sees the same settings the service was constructed with."""
    captured: dict[str, Any] = {}

    def spy_judge(candidates: list[GenreCandidate], settings: GenreEnrichmentSettings):  # type: ignore[no-untyped-def]
        captured["candidates"] = list(candidates)
        captured["settings"] = settings
        from xfinaudio.genre.judge import decide

        return decide(candidates, settings)

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 0.7},
        min_score_threshold=0.1,
    )
    p = _FakeProvider("a", [_cand("Techno", "a", 0.9)])
    service = EnrichmentService(providers=[p], settings=settings, judge=spy_judge)

    service.enrich(_track())

    assert captured["settings"] is settings
    assert len(captured["candidates"]) == 1


# ---------------------------------------------------------------------------
# LLM tie-breaker wiring (opt-in, default OFF)
# ---------------------------------------------------------------------------


def test_enrichment_service_does_not_invoke_tie_breaker_by_default() -> None:
    """Without a tie_breaker injected and settings.llm_tiebreaker_enabled=False,
    no LLM logic runs. The deterministic decision stands."""
    fetcher_calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        fetcher_calls.append(prompt)
        return {"response": "Should Not Be Used"}

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0},
        margin_threshold=0.05,  # two equal candidates → low_confidence
        llm_tiebreaker_enabled=False,
    )
    tb = LocalLlmTieBreaker(fetcher=fetcher)
    p = _FakeProvider("a", [_cand("Techno", "a", 0.5), _cand("House", "a", 0.5)])
    service = EnrichmentService(providers=[p], settings=settings, tie_breaker=tb)

    decision = service.enrich(_track())

    # low_confidence is True, but the LLM is OFF → no fetcher call.
    assert decision.low_confidence is True
    assert fetcher_calls == []


def test_enrichment_service_invokes_tie_breaker_when_enabled_and_low_confidence() -> None:
    """With settings.llm_tiebreaker_enabled=True and a tie_breaker injected,
    a low_confidence decision with non-empty top_n is upgraded."""
    fetcher_calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        fetcher_calls.append(prompt)
        return {"response": "House"}

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0, "b": 1.0},  # equal trust → equal scores → low_confidence
        margin_threshold=0.05,
        llm_tiebreaker_enabled=True,
    )
    tb = LocalLlmTieBreaker(fetcher=fetcher)
    p = _FakeProvider("a", [_cand("Tech House", "a", 1.0), _cand("House", "b", 1.0)])
    service = EnrichmentService(providers=[p], settings=settings, tie_breaker=tb)

    decision = service.enrich(_track())

    # Deterministic primary is "House" (alphabetical tie-break), then the
    # LLM picks "House" from top_n. Primary stays "House" but the decision
    # is upgraded (low_confidence cleared) because the LLM validated a pick.
    assert decision.primary == "House"
    assert decision.low_confidence is False
    assert len(fetcher_calls) == 1


def test_enrichment_service_keeps_decision_when_tie_breaker_fails() -> None:
    """If the tie-breaker returns invalid/fails, the deterministic decision stands."""

    def bad_fetcher(prompt: str) -> dict[str, Any]:
        return {"response": "Wrong Answer"}  # not in top_n

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0, "b": 1.0},
        margin_threshold=0.05,
        llm_tiebreaker_enabled=True,
    )
    tb = LocalLlmTieBreaker(fetcher=bad_fetcher)
    p = _FakeProvider("a", [_cand("Tech House", "a", 1.0), _cand("House", "b", 1.0)])
    service = EnrichmentService(providers=[p], settings=settings, tie_breaker=tb)

    decision = service.enrich(_track())

    # Deterministic primary is "House" (alphabetical tie-break). The LLM fails
    # to pick a valid candidate, so the decision stands: primary="House",
    # low_confidence still True.
    assert decision.primary == "House"
    assert decision.low_confidence is True


def test_enrichment_service_auto_constructs_tie_breaker_when_settings_enabled() -> None:
    """With settings.llm_tiebreaker_enabled=True and no tie_breaker injected,
    the service auto-constructs one from settings.llm_tiebreaker_url/model."""
    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0},
        llm_tiebreaker_enabled=True,
        llm_tiebreaker_url="http://localhost:9999/api/generate",
        llm_tiebreaker_model="qwen",
    )
    p = _FakeProvider("a", [_cand("Techno", "a", 0.9)])
    service = EnrichmentService(providers=[p], settings=settings)

    # The service should have auto-constructed a tie-breaker.
    assert service.tie_breaker is not None
    assert service.tie_breaker._url == "http://localhost:9999/api/generate"
    assert service.tie_breaker._model == "qwen"


def test_enrichment_service_no_tie_breaker_when_settings_disabled() -> None:
    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0},
        llm_tiebreaker_enabled=False,
    )
    p = _FakeProvider("a", [_cand("Techno", "a", 0.9)])
    service = EnrichmentService(providers=[p], settings=settings)

    assert service.tie_breaker is None


def test_enrichment_service_tie_breaker_not_invoked_when_top_n_empty() -> None:
    """If the deterministic judge produces no top_n (no signal), the LLM is
    not invoked even when enabled."""
    fetcher_calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        fetcher_calls.append(prompt)
        return {"response": "Should Not Be Used"}

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0},
        llm_tiebreaker_enabled=True,
    )
    tb = LocalLlmTieBreaker(fetcher=fetcher)
    p = _FakeProvider("a", [])  # no candidates → empty top_n
    service = EnrichmentService(providers=[p], settings=settings, tie_breaker=tb)

    decision = service.enrich(_track())

    assert decision.primary is None
    assert decision.top_n == ()
    assert fetcher_calls == []


def test_enrichment_service_tie_breaker_not_invoked_when_decision_confident() -> None:
    """If the deterministic decision is NOT low_confidence, the LLM is
    not invoked even when enabled (deterministic wins)."""
    fetcher_calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        fetcher_calls.append(prompt)
        return {"response": "Should Not Be Used"}

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0, "b": 0.1},  # very asymmetric → large margin
        margin_threshold=0.05,
        llm_tiebreaker_enabled=True,
    )
    tb = LocalLlmTieBreaker(fetcher=fetcher)
    p = _FakeProvider("a", [_cand("Tech House", "a", 1.0), _cand("House", "b", 1.0)])
    service = EnrichmentService(providers=[p], settings=settings, tie_breaker=tb)

    decision = service.enrich(_track())

    assert decision.primary == "Tech House"
    assert decision.low_confidence is False
    assert fetcher_calls == []


def test_enrichment_service_tie_breaker_failure_does_not_propagate() -> None:
    """A tie-breaker exception is caught and the deterministic decision is returned."""

    def bad_fetcher(prompt: str) -> dict[str, Any]:
        raise RuntimeError("ollama down")

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True},
        source_trust={"a": 1.0, "b": 1.0},
        margin_threshold=0.05,
        llm_tiebreaker_enabled=True,
    )
    tb = LocalLlmTieBreaker(fetcher=bad_fetcher)
    p = _FakeProvider("a", [_cand("Tech House", "a", 1.0), _cand("House", "b", 1.0)])
    service = EnrichmentService(providers=[p], settings=settings, tie_breaker=tb)

    # Must not raise; the deterministic decision stands.
    decision = service.enrich(_track())

    assert decision.primary == "House"  # alphabetical tie-break
    assert decision.low_confidence is True


def test_enrichment_service_constructor_does_not_invoke_tie_breaker() -> None:
    """The tie-breaker is held but not invoked at construction time."""
    fetcher_calls: list[str] = []

    def fetcher(prompt: str) -> dict[str, Any]:
        fetcher_calls.append(prompt)
        return {"response": "x"}

    settings = GenreEnrichmentSettings(
        enabled=True,
        llm_tiebreaker_enabled=True,
    )
    EnrichmentService(settings=settings, tie_breaker=LocalLlmTieBreaker(fetcher=fetcher))

    assert fetcher_calls == []
