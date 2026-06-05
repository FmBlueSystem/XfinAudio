import pytest

from xfinaudio.recommendation.scoring import ScoringWeights
from xfinaudio.recommendation.strategies import (
    PlaylistStrategy,
    StrategyRegistry,
    available_strategies,
    default_strategy_registry,
    get_strategy,
)

EXPECTED_STRATEGIES = {
    "harmonic_journey",
    "warmup",
    "build",
    "peak_time",
    "chill",
    "same_energy",
    "same_vibe",
}


def test_available_strategies_contains_supported_strategy_names() -> None:
    assert set(available_strategies()) == EXPECTED_STRATEGIES


@pytest.mark.parametrize("name", sorted(EXPECTED_STRATEGIES))
def test_get_strategy_returns_profile_with_weights_and_hints(name: str) -> None:
    strategy = get_strategy(name)

    assert strategy.name == name
    assert isinstance(strategy.weights, ScoringWeights)
    assert strategy.display_name
    assert strategy.description


def test_warmup_prefers_low_mid_energy() -> None:
    strategy = get_strategy("warmup")

    assert strategy.energy_range == (1, 6)
    assert strategy.sort_hint == "energy_ascending"


def test_build_prefers_ascending_energy() -> None:
    strategy = get_strategy("build")

    assert strategy.sort_hint == "energy_ascending"
    assert strategy.prefer_energy_direction == "ascending"


def test_peak_time_prefers_high_energy() -> None:
    strategy = get_strategy("peak_time")

    assert strategy.energy_range == (7, 10)
    assert strategy.weights.energy >= strategy.weights.bpm


def test_chill_prefers_lower_energy_and_bpm() -> None:
    strategy = get_strategy("chill")

    assert strategy.energy_range == (1, 5)
    assert strategy.bpm_range == (0.0, 118.0)


def test_same_energy_uses_energy_tolerance() -> None:
    strategy = get_strategy("same_energy")

    assert strategy.energy_tolerance == 1
    assert strategy.weights.energy > strategy.weights.harmonic


def test_same_vibe_requires_tags_or_genre_and_can_degrade() -> None:
    strategy = get_strategy("same_vibe")

    assert strategy.requires_vibe_metadata is True
    assert strategy.degrade_without_vibe_metadata is True
    assert strategy.weights.tags > strategy.weights.harmonic


def test_harmonic_journey_emphasizes_harmonic_weight() -> None:
    strategy = get_strategy("harmonic_journey")

    assert strategy.weights.harmonic > strategy.weights.bpm
    assert strategy.weights.harmonic > strategy.weights.energy
    assert strategy.weights.harmonic > strategy.weights.tags


def test_get_strategy_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown playlist strategy"):
        get_strategy("unknown")


def test_default_strategy_registry_lists_all_current_strategies() -> None:
    registry = default_strategy_registry()

    assert set(registry.available()) == EXPECTED_STRATEGIES


def test_strategy_registry_lookup_returns_existing_profiles() -> None:
    registry = default_strategy_registry()

    assert registry.get("warmup") == get_strategy("warmup")


def test_strategy_registry_accepts_custom_strategy_profile() -> None:
    strategy = PlaylistStrategy(
        name="custom_peak",
        display_name="Custom Peak",
        description="Custom release-safe strategy extension.",
        weights=ScoringWeights(harmonic=0.30, bpm=0.20, energy=0.40, tags=0.10),
    )
    registry = StrategyRegistry([strategy])

    assert registry.get("custom_peak") == strategy


def test_strategy_registry_rejects_duplicate_registration() -> None:
    strategy = get_strategy("warmup")
    registry = StrategyRegistry([strategy])

    with pytest.raises(ValueError, match="Duplicate playlist strategy"):
        registry.register(strategy)


def test_strategy_registry_rejects_unknown_strategy() -> None:
    registry = default_strategy_registry()

    with pytest.raises(ValueError, match="Unknown playlist strategy"):
        registry.get("unknown")
