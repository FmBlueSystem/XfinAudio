"""Settings block for the genre enrichment feature.

Default is fully inert (``enabled = False``, no providers on, no API keys,
LLM tie-breaker off). Enabling any provider or the LLM requires an explicit
entry by the user, so simply upgrading the app does not start any network
or local-cache work.

License posture
---------------
All runtime providers (Last.fm, Spotify, Deezer) are user-keyed, runtime-only.
API keys live in this settings block which is persisted to the user's app
data dir (never in repo assets). The shipped app is 100% CC0; provider data
is fetched on demand and stays in the per-user cache.

The LLM tie-breaker targets a local Ollama/llama.cpp endpoint. Cloud LLMs
are not supported to preserve the project's no-online-dependency posture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_LLM_TIEBREAKER_URL = "http://localhost:11434/api/generate"
DEFAULT_LLM_TIEBREAKER_MODEL = "llama3"


class GenreEnrichmentSettings(BaseModel):
    """Configuration for the multi-source genre enrichment pipeline.

    Whole-feature opt-in via ``enabled``; per-provider opt-in via ``providers``
    (a name -> bool map mirroring registered :class:`GenreProvider.name`).
    Per-provider API keys live in ``api_keys``; providers without a key
    return no candidates (graceful no-op) instead of raising.

    The LLM tie-breaker block is fully opt-in and defaults OFF. It is invoked
    only when the user enables it, the judge produces a ``low_confidence``
    decision, and ``top_n`` is non-empty. The local endpoint URL and model
    name are user-configurable; defaults point at Ollama.
    """

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    providers: dict[str, bool] = Field(default_factory=dict)
    api_keys: dict[str, str] = Field(default_factory=dict)
    source_trust: dict[str, float] = Field(
        default_factory=lambda: {
            "discogs": 1.0,
            "musicbrainz_genres": 0.9,
            "musicbrainz_tags": 0.5,
        }
    )
    min_score_threshold: float = Field(default=0.2, ge=0.0)
    margin_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    low_confidence_floor: float = Field(default=0.4, ge=0.0, le=1.0)
    llm_tiebreaker_enabled: bool = False
    llm_tiebreaker_url: str = DEFAULT_LLM_TIEBREAKER_URL
    llm_tiebreaker_model: str = DEFAULT_LLM_TIEBREAKER_MODEL


__all__ = [
    "DEFAULT_LLM_TIEBREAKER_MODEL",
    "DEFAULT_LLM_TIEBREAKER_URL",
    "GenreEnrichmentSettings",
]
