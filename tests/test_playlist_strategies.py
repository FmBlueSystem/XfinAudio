import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist
from xfinaudio.recommendation.scoring import ScoringWeights
from xfinaudio.recommendation.strategies import (
    PlaylistStrategy,
    StrategyRegistry,
    available_strategies,
    default_strategy_registry,
    get_strategy,
    resolve_strategy_name,
)

EXPECTED_STRATEGIES = {
    "harmonic_journey",
    "warmup",
    "build",
    "peak_time",
    "chill",
    "same_energy",
    "same_vibe",
    "same_color",
    "same_genre",
    "same_color_energy",
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


def test_same_color_energy_registers_with_expected_profile() -> None:
    strategy = get_strategy("same_color_energy")

    assert strategy.display_name == "Same Color & Energy"
    assert strategy.energy_tolerance == 1
    assert strategy.weights == ScoringWeights(harmonic=0.25, bpm=0.15, energy=0.30, tags=0.10, spectral=0.20)


def test_strategy_descriptions_state_guarantees() -> None:
    same_color_energy_description = get_strategy("same_color_energy").description.lower()
    assert "color" in same_color_energy_description
    assert "±1" in same_color_energy_description or "+/-1" in same_color_energy_description

    same_color_description = get_strategy("same_color").description.lower()
    assert "only tracks matching" in same_color_description
    assert "energy" in same_color_description and "not" in same_color_description

    same_energy_description = get_strategy("same_energy").description.lower()
    assert "±1" in same_energy_description or "+/-1" in same_energy_description
    assert "color" in same_energy_description and "not" in same_energy_description


def test_same_genre_constrains_to_anchor_primary_genre() -> None:
    strategy = get_strategy("same_genre")

    assert strategy.display_name == "Same Genre"
    assert strategy.description == "Constrain the playlist to the dominant primary genre of the anchor tracks."
    assert strategy.weights == ScoringWeights(harmonic=0.30, bpm=0.20, energy=0.20, tags=0.30)
    assert strategy.sort_hint == "path"
    assert strategy.energy_range is None
    assert strategy.bpm_range is None
    assert strategy.requires_vibe_metadata is False


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


def _track(title: str, energy: int | None = None, path: str | None = None) -> TrackRecord:
    return TrackRecord(
        path=path or f"/{title}.flac",
        title=title,
        energy_level=energy,
        metadata_status="complete",
    )


def test_same_energy_filters_candidates_outside_anchor_energy_tolerance() -> None:
    tracks = [
        _track("anchor", energy=5, path="/anchor.flac"),
        _track("near_low", energy=4),
        _track("near_same", energy=5),
        _track("near_high", energy=6),
        _track("too_low", energy=1),
        _track("too_high", energy=9),
    ]

    result = recommend_playlist(
        tracks,
        "same_energy",
        DJControls(start_path="/anchor.flac"),
    )

    titles = [track.title for track in result.ordered_tracks]
    assert "too_low" not in titles
    assert "too_high" not in titles
    assert {"anchor", "near_low", "near_same", "near_high"}.issubset(set(titles))


def test_resolve_strategy_name_accepts_internal_name() -> None:
    assert resolve_strategy_name("harmonic_journey") == "harmonic_journey"


def test_resolve_strategy_name_accepts_display_name() -> None:
    assert resolve_strategy_name("Harmonic Journey") == "harmonic_journey"


def test_resolve_strategy_name_rejects_unknown_label() -> None:
    with pytest.raises(ValueError, match="Unknown playlist strategy"):
        resolve_strategy_name("Harmonic Journey!!!")
