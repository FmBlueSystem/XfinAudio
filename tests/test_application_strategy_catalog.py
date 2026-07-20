"""Tests for the application-level strategy catalog boundary."""

from __future__ import annotations

from xfinaudio.application.strategy_catalog import describe_strategy, list_strategy_catalog


def test_list_strategy_catalog_returns_display_entries() -> None:
    entries = list_strategy_catalog()

    assert entries
    assert entries[0].name == "harmonic_journey"
    assert entries[0].display_name == "Harmonic Journey"
    assert entries[0].description
    assert isinstance(entries[0].requires_vibe_metadata, bool)


def test_describe_strategy_returns_description_or_empty_fallback() -> None:
    assert "energy" in describe_strategy("build").lower()
    assert describe_strategy("unknown") == ""


def test_list_strategy_catalog_includes_same_color_energy() -> None:
    entries = list_strategy_catalog()

    matching = [entry for entry in entries if entry.name == "same_color_energy"]
    assert len(matching) == 1
    assert matching[0].display_name == "Same Color & Energy"
