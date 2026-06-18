"""Deterministic weighted-vote consensus judge for genre candidates.

The judge is a pure function: same inputs always produce the same
:class:`GenreDecision`. It is the single source of truth for which canonical
genre a track belongs to and how confident that decision is.

An optional :func:`decide_with_llm` helper upgrades a ``low_confidence``
decision by asking a local LLM tie-breaker to pick one of the already-
normalized ``top_n`` candidates. The deterministic judge remains the system
of record; the LLM is opt-in and never invents genres.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xfinaudio.genre.models import GenreCandidate, GenreDecision, GenreProvenance
from xfinaudio.genre.normalizer import UNMAPPED
from xfinaudio.genre.settings import GenreEnrichmentSettings

if TYPE_CHECKING:  # pragma: no cover - import-only, avoids runtime cycle
    from xfinaudio.genre.llm_judge import LocalLlmTieBreaker


_ENABLED_RUNTIME_SOURCE_TRUST: dict[str, float] = {
    "lastfm": 0.6,
    "spotify": 0.6,
    "deezer": 0.4,
}


def decide(
    candidates: list[GenreCandidate] | tuple[GenreCandidate, ...],
    settings: GenreEnrichmentSettings,
) -> GenreDecision:
    """Resolve ``candidates`` into a :class:`GenreDecision` via weighted vote.

    ``score(g) = Σ_source ( source_trust[source] × candidate.confidence )`` for
    candidates whose canonical genre is ``g``. The primary is the argmax.
    ``top_n`` is the deterministic ranking of all candidates above
    ``min_score_threshold``. ``confidence`` is the primary's score as a fraction
    of total mass (clamped to ``[0, 1]``). ``low_confidence`` is set when the
    #1 vs #2 margin is thinner than ``margin_threshold`` or total mass falls
    below ``low_confidence_floor``.
    """
    mappable = tuple(c for c in candidates if c.canonical_genre and c.canonical_genre != UNMAPPED)

    if not mappable:
        return GenreDecision(
            primary=None,
            top_n=(),
            confidence=0.0,
            low_confidence=True,
            provenance=GenreProvenance(
                candidates=tuple(candidates),
                source_trust=dict(settings.source_trust),
                scores={},
            ),
        )

    scores: dict[str, float] = {}
    for c in mappable:
        trust = settings.source_trust.get(c.source, _runtime_trust(c.source, settings))
        scores[c.canonical_genre] = scores.get(c.canonical_genre, 0.0) + trust * c.confidence

    above_threshold = {g: s for g, s in scores.items() if s >= settings.min_score_threshold}
    considered = above_threshold if above_threshold else scores

    # Stable sort: descending by score, ascending by canonical name (deterministic).
    ordered = sorted(considered.items(), key=lambda kv: (-kv[1], kv[0]))

    primary = ordered[0][0]
    top_n = tuple(g for g, _ in ordered)

    total_score = sum(scores.values())
    confidence = (ordered[0][1] / total_score) if total_score > 0 else 0.0
    confidence = max(0.0, min(1.0, confidence))

    low_confidence = False
    if len(ordered) >= 2:
        margin = ordered[0][1] - ordered[1][1]
        if margin < settings.margin_threshold:
            low_confidence = True
    if total_score < settings.low_confidence_floor:
        low_confidence = True

    return GenreDecision(
        primary=primary,
        top_n=top_n,
        confidence=confidence,
        low_confidence=low_confidence,
        provenance=GenreProvenance(
            candidates=mappable,
            source_trust=dict(settings.source_trust),
            scores=scores,
        ),
    )


def _runtime_trust(source: str, settings: GenreEnrichmentSettings) -> float:
    if settings.providers.get(source, False):
        return _ENABLED_RUNTIME_SOURCE_TRUST.get(source, 0.0)
    return 0.0


def decide_with_llm(
    decision: GenreDecision,
    tie_breaker: LocalLlmTieBreaker | None,
) -> GenreDecision:
    """Upgrade a ``low_confidence`` decision using a local LLM tie-breaker.

    The deterministic decision is the system of record. The LLM is invoked
    only when:
      - ``tie_breaker`` is not None,
      - ``decision.low_confidence`` is True,
      - ``decision.top_n`` is non-empty.

    If the model picks a candidate that is in ``top_n``, the decision is
    rewritten with that candidate as the new ``primary`` and
    ``low_confidence`` cleared. Otherwise the input decision is returned
    unchanged.
    """
    if tie_breaker is None or not decision.low_confidence or not decision.top_n:
        return decision
    chosen = tie_breaker.break_tie(decision=decision)
    if chosen is None:
        return decision
    return decision.model_copy(update={"primary": chosen, "low_confidence": False})


__all__ = ["decide", "decide_with_llm"]
