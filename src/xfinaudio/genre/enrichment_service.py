"""Orchestrates providers -> judge -> (optional) LLM tie-breaker -> decision.

The enrichment service is the only piece of the genre package that performs I/O
(network or per-user cache). All upstream consumers (scan, recommendation,
health) call :meth:`EnrichmentService.enrich` and treat the returned
:class:`GenreDecision` as immutable.

The LLM tie-breaker is **opt-in, default OFF**:

- When ``settings.llm_tiebreaker_enabled`` is ``False`` (the default), no
  tie-breaker is constructed or invoked. The deterministic judge is the
  system of record.
- When the flag is ``True``, the service either uses the injected
  ``tie_breaker`` or auto-constructs one from
  ``settings.llm_tiebreaker_url`` and ``settings.llm_tiebreaker_model``.
- The tie-breaker is only invoked when the deterministic decision is
  ``low_confidence`` AND ``top_n`` is non-empty.
- Any failure (exception, invalid response, network error) leaves the
  deterministic decision intact. The LLM can only UPGRADE a decision.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import suppress
from typing import Any

from xfinaudio.genre.judge import decide, decide_with_llm
from xfinaudio.genre.llm_judge import LocalLlmTieBreaker
from xfinaudio.genre.models import GenreCandidate, GenreDecision
from xfinaudio.genre.providers.base import GenreProvider
from xfinaudio.genre.settings import GenreEnrichmentSettings

JudgeFn = Callable[[list[GenreCandidate], GenreEnrichmentSettings], GenreDecision]


class EnrichmentService:
    """Run enabled providers for a track, judge their candidates, and (optionally)
    consult a local LLM tie-breaker for low-confidence decisions.

    When ``settings.enabled`` is ``False`` the service is a no-op (no
    providers are queried). When a provider raises, its failure is isolated
    and the remaining providers' candidates are still judged.
    """

    def __init__(
        self,
        *,
        providers: Iterable[GenreProvider] = (),
        settings: GenreEnrichmentSettings | None = None,
        judge: JudgeFn = decide,
        tie_breaker: LocalLlmTieBreaker | None = None,
    ) -> None:
        self._providers: tuple[GenreProvider, ...] = tuple(providers)
        self._settings: GenreEnrichmentSettings = settings if settings is not None else GenreEnrichmentSettings()
        self._judge: JudgeFn = judge
        # Tie-breaker rule: the user's settings flag is the GATE. An injected
        # tie_breaker is only used when the flag is enabled. When the flag is
        # enabled and no tie_breaker was injected, auto-construct one from
        # settings.llm_tiebreaker_url + model. This keeps the LLM strictly
        # opt-in: an injection alone never activates the feature.
        if self._settings.llm_tiebreaker_enabled:
            self._tie_breaker: LocalLlmTieBreaker | None = (
                tie_breaker
                if tie_breaker is not None
                else LocalLlmTieBreaker(
                    url=self._settings.llm_tiebreaker_url,
                    model=self._settings.llm_tiebreaker_model,
                )
            )
        else:
            self._tie_breaker = None

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @property
    def settings(self) -> GenreEnrichmentSettings:
        return self._settings

    @property
    def tie_breaker(self) -> LocalLlmTieBreaker | None:
        """The LLM tie-breaker in use, or ``None`` when disabled."""
        return self._tie_breaker

    def enrich(self, track: Any) -> GenreDecision:
        if not self._settings.enabled:
            return GenreDecision()

        candidates: list[GenreCandidate] = []
        for provider in self._providers:
            if not self._settings.providers.get(provider.name, False):
                continue
            try:
                candidates.extend(provider.fetch(track))
            except Exception:
                # Provider failure is isolated (spec Scenario 2.3).
                continue

        decision = self._judge(candidates, self._settings)
        if self._tie_breaker is not None:
            # Tie-breaker failure must never propagate; the deterministic
            # decision is the system of record.
            with suppress(Exception):
                decision = decide_with_llm(decision, self._tie_breaker)
        return decision


__all__ = ["EnrichmentService", "JudgeFn"]
