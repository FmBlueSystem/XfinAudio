"""Frozen Pydantic models for the genre enrichment pipeline.

These models are the wire format between providers, the consensus judge, the
enrichment service, persistence, and the UI. All are immutable; updates use
``model_copy(update=...)`` per the project's immutability rule.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GenreCandidate(BaseModel):
    """A single source's vote for a track's genre.

    ``canonical_genre`` is already resolved through the taxonomy/crosswalk and
    is one of the canonical genre names (or :data:`UNMAPPED` from the
    normalizer). ``confidence`` is the source-internal certainty in ``[0, 1]``.
    """

    model_config = ConfigDict(frozen=True)

    canonical_genre: str = Field(min_length=1)
    raw_label: str
    source: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class GenreProvenance(BaseModel):
    """Audit trail for a :class:`GenreDecision`.

    ``candidates`` is the full set of votes considered. ``source_trust`` records
    the per-source trust prior used at decision time. ``scores`` records the
    final weighted score per canonical genre (empty when no candidates).
    """

    model_config = ConfigDict(frozen=True)

    candidates: tuple[GenreCandidate, ...] = Field(default_factory=tuple)
    source_trust: dict[str, float] = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)


class GenreDecision(BaseModel):
    """Resolved canonical genre decision for a track.

    ``primary`` is the decided canonical genre (or ``None`` when no signal).
    ``top_n`` is the ranked list of canonical genres above the judge threshold,
    in score order. ``confidence`` is in ``[0, 1]``. ``low_confidence`` is set
    when the top-1 vs top-2 margin is thin or total evidence is weak.
    """

    model_config = ConfigDict(frozen=True)

    primary: str | None = None
    top_n: tuple[str, ...] = Field(default_factory=tuple)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    low_confidence: bool = False
    provenance: GenreProvenance = Field(default_factory=GenreProvenance)


__all__ = ["GenreCandidate", "GenreDecision", "GenreProvenance"]
