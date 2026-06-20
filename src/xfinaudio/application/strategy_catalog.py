"""Application boundary for playlist strategy catalog display data."""

from __future__ import annotations

from dataclasses import dataclass

from xfinaudio.recommendation.strategies import default_strategy_registry


@dataclass(frozen=True)
class StrategyCatalogEntry:
    """Public application DTO for strategy display data."""

    name: str
    display_name: str
    description: str
    requires_vibe_metadata: bool


def list_strategy_catalog() -> list[StrategyCatalogEntry]:
    """Return built-in playlist strategies in display order."""
    registry = default_strategy_registry()
    return [
        StrategyCatalogEntry(
            name=strategy.name,
            display_name=strategy.display_name,
            description=strategy.description,
            requires_vibe_metadata=strategy.requires_vibe_metadata,
        )
        for strategy in (registry.get(name) for name in registry.available())
    ]


def describe_strategy(strategy_name: str) -> str:
    """Return a strategy description, or an empty fallback for unknown input."""
    try:
        return default_strategy_registry().get(strategy_name).description
    except ValueError:
        return ""


__all__ = ["StrategyCatalogEntry", "describe_strategy", "list_strategy_catalog"]
