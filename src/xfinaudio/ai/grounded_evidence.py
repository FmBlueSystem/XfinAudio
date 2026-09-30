"""Optional commentary over explicit facts, never metadata/ranking decisions."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from xfinaudio.ai.nan_client import Transport
from xfinaudio.ai.privacy import redact_paths
from xfinaudio.ai.structured_common import _ERROR, ask_object


class _Fact(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", allow_inf_nan=False)


class _MetadataFact(_Fact):
    id: Literal["m0"]
    track_count: int = Field(ge=0, le=1_000_000)
    missing_bpm: int = Field(ge=0)
    missing_key: int = Field(ge=0)
    missing_energy: int = Field(ge=0)
    locked_with_gaps: int = Field(ge=0)

    @model_validator(mode="after")
    def coverage_bounds(self) -> _MetadataFact:
        if max(self.missing_bpm, self.missing_key, self.missing_energy, self.locked_with_gaps) > self.track_count:
            raise ValueError("Gap counts exceed the supplied track count")
        return self


class _LiveFact(_Fact):
    id: str = Field(pattern=r"^c\d{1,2}$")
    rank: int = Field(ge=1, le=20)
    score: float = Field(ge=0, le=1)
    bpm_delta: float | None = Field(ge=0, le=40_000)
    energy_delta: float | None = Field(ge=-10, le=10)
    readiness: Literal["ready"]


class _Commentary(_Fact):
    commentary: str = Field(min_length=1, max_length=1200)
    fact_ids: list[str] = Field(min_length=1, max_length=20)


def explain_grounded_evidence(
    kind: Literal["metadata", "live"],
    facts: Sequence[dict[str, object]],
    *,
    transport: Transport | None = None,
    timeout: float = 30.0,
) -> str:
    """Return brief AI commentary for display alongside authoritative local facts.

    Grounding IDs and payload shape are enforced; prose is still a model's
    interpretation. Callers label it accordingly and never parse it into actions.
    """
    if kind not in {"metadata", "live"} or not 1 <= len(facts) <= (1 if kind == "metadata" else 20):
        raise ValueError("Choose supported, bounded local evidence for AI commentary.")
    try:
        models: list[_MetadataFact] | list[_LiveFact]
        models = (
            [_MetadataFact.model_validate(fact) for fact in facts]
            if kind == "metadata"
            else [_LiveFact.model_validate(fact) for fact in facts]
        )
    except ValidationError:
        raise ValueError("Local evidence is invalid or contains unsupported fields.") from None
    ids = {fact.id for fact in models}
    if len(ids) != len(models):
        raise ValueError("Evidence references must be unique.")
    if kind == "live" and [fact["rank"] for fact in facts] != list(range(1, len(facts) + 1)):
        raise ValueError("Candidate facts must preserve the local ranking.")
    context = {"kind": kind, "facts": [fact.model_dump(mode="json") for fact in models]}
    detail = (
        "Explain why absent BPM prevents tempo checking, absent key prevents harmonic checking, "
        "and absent energy prevents progression checking. Actual repair priority is locked tracks first, "
        "then fewer missing fields. No per-track data is supplied; do not name tracks or invent tag values."
        if kind == "metadata"
        else "Explain the existing candidate ranking from supplied scores and deltas only. "
        "Candidate IDs map to the displayed ranks; readiness belongs to the local validator. "
        "Do not claim transition timing, cue points, audio analysis or safety beyond those facts."
    )
    data = ask_object(
        "Explain these local facts briefly in Spanish.",
        context,
        'Schema: {"commentary": plain text up to 1200 characters and 150 words, '
        '"fact_ids": nonempty list of referenced supplied IDs}. '
        "Never invent facts, missing values, scores or numerical claims. Never change tags, ranking, "
        "playback or readiness. Unknown metrics remain unknown. " + detail,
        transport=transport,
        timeout=timeout,
    )
    try:
        result = _Commentary.model_validate(data)
    except ValidationError:
        raise ValueError(_ERROR) from None
    text = result.commentary.strip()
    refs = result.fact_ids
    if (
        not text
        or len(text.split()) > 150
        or redact_paths(text) != text
        or set(refs) - ids
        or len(set(refs)) != len(refs)
        or set(re.findall(r"\b[cm]\d+\b", text, re.IGNORECASE)) - ids
    ):
        raise ValueError(_ERROR)
    return text
