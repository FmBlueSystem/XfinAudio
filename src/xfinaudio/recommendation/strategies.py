"""Playlist strategy profiles for product-level recommendation intent."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from xfinaudio.recommendation.scoring import ScoringWeights

StrategyName = Literal[
    "harmonic_journey",
    "warmup",
    "build",
    "peak_time",
    "chill",
    "same_energy",
    "same_vibe",
    "same_color",
    "same_genre",
]
SortHint = Literal["path", "energy_ascending", "energy_descending", "bpm_ascending"]


class PlaylistStrategy(BaseModel):
    """Pure recommendation policy profile selected by the DJ."""

    model_config = ConfigDict(frozen=True)

    name: str
    display_name: str
    description: str
    weights: ScoringWeights
    energy_range: tuple[int, int] | None = None
    bpm_range: tuple[float, float] | None = None
    energy_tolerance: int | None = None
    sort_hint: SortHint = "path"
    requires_vibe_metadata: bool = False
    degrade_without_vibe_metadata: bool = False


_STRATEGIES: dict[StrategyName, PlaylistStrategy] = {
    "harmonic_journey": PlaylistStrategy(
        name="harmonic_journey",
        display_name="Harmonic Journey",
        description="Prioritize Camelot-compatible movement while keeping BPM and energy smooth.",
        weights=ScoringWeights(harmonic=0.60, bpm=0.20, energy=0.15, tags=0.05),
    ),
    "warmup": PlaylistStrategy(
        name="warmup",
        display_name="Warmup",
        description="Start controlled with lower-to-mid energy tracks.",
        weights=ScoringWeights(harmonic=0.35, bpm=0.25, energy=0.30, tags=0.10),
        energy_range=(1, 6),
        sort_hint="energy_ascending",
    ),
    "build": PlaylistStrategy(
        name="build",
        display_name="Build",
        description="Prefer a gradually rising energy curve.",
        weights=ScoringWeights(harmonic=0.35, bpm=0.20, energy=0.35, tags=0.10),
        sort_hint="energy_ascending",
    ),
    "peak_time": PlaylistStrategy(
        name="peak_time",
        display_name="Peak Time",
        description="Focus the recommendation on high-energy records.",
        weights=ScoringWeights(harmonic=0.35, bpm=0.20, energy=0.35, tags=0.10),
        energy_range=(7, 10),
        sort_hint="energy_descending",
    ),
    "chill": PlaylistStrategy(
        name="chill",
        display_name="Chill",
        description="Prefer lower energy and lower BPM selections.",
        weights=ScoringWeights(harmonic=0.30, bpm=0.35, energy=0.25, tags=0.10),
        energy_range=(1, 5),
        bpm_range=(0.0, 118.0),
        sort_hint="bpm_ascending",
    ),
    "same_energy": PlaylistStrategy(
        name="same_energy",
        display_name="Same Energy",
        description="Keep the playlist close to a stable energy band.",
        weights=ScoringWeights(harmonic=0.20, bpm=0.20, energy=0.50, tags=0.10),
        energy_tolerance=1,
    ),
    "same_vibe": PlaylistStrategy(
        name="same_vibe",
        display_name="Same Vibe",
        description="Emphasize shared tags and genre when vibe metadata exists.",
        weights=ScoringWeights(harmonic=0.20, bpm=0.15, energy=0.15, tags=0.50),
        requires_vibe_metadata=True,
        degrade_without_vibe_metadata=True,
    ),
    "same_color": PlaylistStrategy(
        name="same_color",
        display_name="Same Color",
        description="Prioritize tracks with similar spectral color profiles for a cohesive timbre.",
        weights=ScoringWeights(harmonic=0.30, bpm=0.20, energy=0.20, tags=0.10, spectral=0.20),
    ),
    "same_genre": PlaylistStrategy(
        name="same_genre",
        display_name="Same Genre",
        description="Constrain the playlist to the dominant primary genre of the anchor tracks.",
        weights=ScoringWeights(harmonic=0.30, bpm=0.20, energy=0.20, tags=0.30),
        sort_hint="path",
    ),
}


class StrategyRegistry:
    """Registry seam for playlist strategy lookup and product extension."""

    def __init__(self, strategies: Iterable[PlaylistStrategy] = ()) -> None:
        self._strategies: dict[str, PlaylistStrategy] = {}
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy: PlaylistStrategy) -> None:
        """Register a strategy profile by name."""
        if strategy.name in self._strategies:
            raise ValueError(f"Duplicate playlist strategy: {strategy.name}")
        self._strategies[str(strategy.name)] = strategy

    def available(self) -> list[str]:
        """Return registered strategy names in registration order."""
        return list(self._strategies)

    def resolve_name(self, name: str) -> str:
        """Return the internal strategy name for an internal name or display label."""
        if name in self._strategies:
            return name
        for strategy in self._strategies.values():
            if strategy.display_name == name:
                return strategy.name
        raise ValueError(f"Unknown playlist strategy: {name}")

    def get(self, name: str) -> PlaylistStrategy:
        """Return a registered strategy profile by internal name or display label."""
        return self._strategies[self.resolve_name(name)]


def default_strategy_registry() -> StrategyRegistry:
    """Return a registry containing all built-in strategy profiles."""
    return StrategyRegistry(_STRATEGIES.values())


def available_strategies() -> list[StrategyName]:
    """Return supported playlist strategy names in display order."""
    return list(_STRATEGIES)


def resolve_strategy_name(name: str, strategy_registry: StrategyRegistry | None = None) -> str:
    """Return the internal strategy name for an internal name or display label."""
    return (strategy_registry or default_strategy_registry()).resolve_name(name)


def get_strategy(name: str) -> PlaylistStrategy:
    """Return a playlist strategy profile by internal name or display label."""
    return default_strategy_registry().get(name)


__all__ = [
    "PlaylistStrategy",
    "StrategyName",
    "StrategyRegistry",
    "available_strategies",
    "default_strategy_registry",
    "get_strategy",
    "resolve_strategy_name",
]
