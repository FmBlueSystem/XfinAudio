"""Tests for the settings extension (PR1 Task 1.1).

Covers spec Requirement 1 Scenarios 1.1-1.3.
"""

from __future__ import annotations

from xfinaudio.genre.settings import GenreEnrichmentSettings


def test_settings_default_is_fully_inert() -> None:
    settings = GenreEnrichmentSettings()

    assert settings.enabled is False
    assert settings.providers == {}
    assert settings.api_keys == {}
    assert settings.llm_tiebreaker_enabled is False
    # Local Ollama defaults
    assert settings.llm_tiebreaker_url.startswith("http://localhost")
    assert settings.llm_tiebreaker_model  # non-empty


def test_settings_per_provider_enable_flag() -> None:
    settings = GenreEnrichmentSettings(providers={"lastfm": True, "spotify": False, "deezer": True})

    assert settings.providers["lastfm"] is True
    assert settings.providers["spotify"] is False
    assert settings.providers["deezer"] is True


def test_settings_per_provider_api_key_storage() -> None:
    settings = GenreEnrichmentSettings(
        api_keys={"lastfm": "sk-abc", "spotify": "client-id:client-secret"},
    )

    assert settings.api_keys["lastfm"] == "sk-abc"
    assert settings.api_keys["spotify"] == "client-id:client-secret"


def test_settings_llm_tiebreaker_block() -> None:
    settings = GenreEnrichmentSettings(
        llm_tiebreaker_enabled=True,
        llm_tiebreaker_url="http://localhost:11434/api/generate",
        llm_tiebreaker_model="llama3",
    )

    assert settings.llm_tiebreaker_enabled is True
    assert settings.llm_tiebreaker_url == "http://localhost:11434/api/generate"
    assert settings.llm_tiebreaker_model == "llama3"


def test_settings_round_trip_through_pydantic() -> None:
    """Pydantic auto-handles new optional fields; serialization round-trips."""
    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"lastfm": True},
        api_keys={"lastfm": "sk-abc"},
        llm_tiebreaker_enabled=True,
    )

    payload = settings.model_dump(mode="json")
    restored = GenreEnrichmentSettings.model_validate(payload)

    assert restored == settings


def test_settings_persistence_does_not_bump_schema() -> None:
    """The new fields are additive; the settings_repository handles them
    via the existing model_validate / model_dump path with no version bump."""
    from xfinaudio.config.settings import CURRENT_SETTINGS_VERSION

    assert CURRENT_SETTINGS_VERSION == 1
