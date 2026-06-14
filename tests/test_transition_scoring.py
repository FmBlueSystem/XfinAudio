import pytest

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.scoring import (
    KeyShiftConfig,
    ScoringWeights,
    ThresholdScore,
    TransitionScore,
    TransitionScoringConfig,
    score_transition,
)


def track(
    path: str,
    *,
    bpm: float | None = 120.0,
    camelot_key: str | None = "8A",
    energy_level: int | None = 5,
    genre: str | None = "House",
    tags: list[str] | None = None,
    missing_required_fields: list[str] | None = None,
    spectral_profile: SpectralProfile | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        genre=genre,
        tags=["Peak", "Vocal"] if tags is None else tags,
        metadata_status="complete" if missing_required_fields is None else "incomplete",
        missing_required_fields=missing_required_fields or [],
        spectral_profile=spectral_profile,
    )


def test_score_transition_scores_bpm_compatibility() -> None:
    result = score_transition(track("left", bpm=120.0), track("right", bpm=123.0))

    assert result.component_scores["bpm"] == pytest.approx(0.902344)
    assert "BPM difference is 2.50%" in result.explanations


def test_score_transition_scores_energy_compatibility() -> None:
    result = score_transition(track("left", energy_level=4), track("right", energy_level=6))

    assert result.component_scores["energy"] == pytest.approx(0.555556)
    assert "Energy level difference is 2" in result.explanations


def test_score_transition_scores_tag_overlap_with_genre() -> None:
    left = track("left", genre="House", tags=["Peak", "Vocal"])
    right = track("right", genre="House", tags=["Peak", "Deep"])

    result = score_transition(left, right)

    assert result.component_scores["tags"] == pytest.approx(0.5)
    assert "Tag overlap is 2/4" in result.explanations


def test_score_transition_redistributes_weight_when_tags_are_missing() -> None:
    left = track("left", genre=None, tags=[])
    right = track("right", genre=None, tags=[])

    result = score_transition(left, right)

    assert "tags" not in result.component_scores
    assert result.total_score == 1.0
    assert "Tag score unavailable; both tracks have no tags or genre" in result.warnings


def test_score_transition_warns_and_returns_zero_when_required_metadata_is_incomplete() -> None:
    result = score_transition(
        track("left", camelot_key=None, missing_required_fields=["camelot_key"]),
        track("right"),
    )

    assert result.total_score == 0.0
    assert "left missing required metadata: camelot_key" in result.warnings


def test_score_transition_combines_weighted_component_scores() -> None:
    left = track("left", bpm=120.0, camelot_key="8A", energy_level=4, genre="House", tags=["Peak", "Vocal"])
    right = track("right", bpm=123.0, camelot_key="8A", energy_level=6, genre="House", tags=["Peak", "Deep"])

    result = score_transition(left, right)

    assert result.total_score == pytest.approx(0.814475)
    assert result.component_scores == {
        "harmonic": 1.0,
        "bpm": pytest.approx(0.902344),
        "energy": pytest.approx(0.555556),
        "tags": 0.5,
    }


def test_score_transition_warns_and_returns_zero_for_invalid_camelot_key() -> None:
    result = score_transition(track("left", camelot_key="not-a-key"), track("right"))

    assert result.total_score == 0.0
    assert "left has invalid Camelot key: not-a-key" in result.warnings


def test_score_transition_accepts_controlled_boost_rules() -> None:
    result = score_transition(
        track("left", camelot_key="8A"), track("right", camelot_key="10A"), boost_rules={("8A", "10A")}
    )

    assert result.component_scores["harmonic"] == 0.8


def test_scoring_weights_reject_non_positive_total_weight() -> None:
    with pytest.raises(ValueError, match="total weight must be greater than zero"):
        ScoringWeights(harmonic=0.0, bpm=0.0, energy=0.0, tags=0.0, spectral=0.0)


def test_scoring_weights_reject_negative_component_weights() -> None:
    with pytest.raises(ValueError, match="component weights cannot be negative"):
        ScoringWeights(harmonic=1.0, bpm=-0.1, energy=0.0, tags=0.0)


def test_score_transition_uses_custom_bpm_thresholds() -> None:
    config = TransitionScoringConfig(
        bpm_thresholds=(ThresholdScore(max_delta=3.0, score=0.2),),
        energy_thresholds=(ThresholdScore(max_delta=10.0, score=1.0),),
    )

    result = score_transition(track("left", bpm=120.0), track("right", bpm=123.0), config=config)

    assert result.component_scores["bpm"] == 0.2


def test_score_transition_uses_custom_energy_thresholds() -> None:
    config = TransitionScoringConfig(
        bpm_thresholds=(ThresholdScore(max_delta=100.0, score=1.0),),
        energy_thresholds=(ThresholdScore(max_delta=2.0, score=0.25),),
    )

    result = score_transition(track("left", energy_level=4), track("right", energy_level=6), config=config)

    assert result.component_scores["energy"] == 0.25


def test_score_transition_default_harmonic_score_is_unchanged_without_key_shift() -> None:
    result = score_transition(track("left", camelot_key="8A"), track("right", camelot_key="6A"))

    assert result.component_scores["harmonic"] == 0.0


def test_score_transition_can_normalize_key_with_pitch_shift() -> None:
    config = TransitionScoringConfig(key_shift=KeyShiftConfig(right_semitones=2))

    result = score_transition(track("left", camelot_key="8A"), track("right", camelot_key="6A"), config=config)

    assert result.component_scores["harmonic"] == 1.0
    assert "Pitch/key normalization shifted right key from 6A to 8A" in result.explanations


def test_fuzzy_bpm_and_energy_scores_are_monotonic() -> None:
    close_bpm = score_transition(track("left", bpm=120.0), track("right", bpm=121.0))
    wider_bpm = score_transition(track("left", bpm=120.0), track("right", bpm=123.0))
    close_energy = score_transition(track("left", energy_level=5), track("right", energy_level=6))
    wider_energy = score_transition(track("left", energy_level=5), track("right", energy_level=7))

    assert close_bpm.component_scores["bpm"] > wider_bpm.component_scores["bpm"]
    assert close_energy.component_scores["energy"] > wider_energy.component_scores["energy"]


def test_score_transition_warns_when_genre_and_tags_do_not_overlap() -> None:
    result = score_transition(
        track("left", genre="Pop & Dance", tags=["Pop & Dance", "Dance-Pop"]),
        track("right", genre="Hip-Hop & R&B", tags=["Hip-Hop & R&B", "Rap"]),
    )

    assert result.component_scores["tags"] == 0.0
    assert "Genre/tag mismatch: no shared genre, subgenre, mood, or tag metadata" in result.warnings


def test_score_transition_returns_cached_result_on_second_call() -> None:
    """Second call with same args returns the exact same object (identity, not just equality)."""
    left = track("left", bpm=120.0, camelot_key="8A", energy_level=5, genre="House", tags=["Peak"])
    right = track("right", bpm=121.0, camelot_key="8A", energy_level=6, genre="House", tags=["Peak"])
    cache: dict[tuple, TransitionScore] = {}

    first = score_transition(left, right, cache=cache)
    second = score_transition(left, right, cache=cache)

    # Identity check: same object returned from cache
    assert first is second
    # Cache has exactly 1 entry (memoized)
    assert len(cache) == 1


def test_score_cache_is_isolated_per_session() -> None:
    """Each session-scoped cache memoizes independently; caches do not share state."""
    left = track("left", bpm=120.0, camelot_key="8A", energy_level=5, genre="House", tags=["Peak"])
    right = track("right", bpm=121.0, camelot_key="8A", energy_level=6, genre="House", tags=["Peak"])
    cache_a: dict[tuple, TransitionScore] = {}
    cache_b: dict[tuple, TransitionScore] = {}

    score_transition(left, right, cache=cache_a)
    score_transition(left, right, cache=cache_b)

    # Each cache populated exactly one entry, independently
    assert len(cache_a) == 1
    assert len(cache_b) == 1
    # The caches are distinct objects (no shared session state)
    assert cache_a is not cache_b


def test_score_transition_includes_high_spectral_score_for_same_color() -> None:
    profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    left = track("left", spectral_profile=profile)
    right = track("right", spectral_profile=profile)

    result = score_transition(left, right)

    assert result.component_scores["spectral"] > 0.7
    assert "Spectral similarity" in " ".join(result.explanations)


def test_score_transition_includes_low_spectral_score_for_different_colors() -> None:
    red = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    green = SpectralProfile(red_ratio=0.05, green_ratio=0.9, blue_ratio=0.05, dominant_color="GREEN")
    left = track("left", spectral_profile=red)
    right = track("right", spectral_profile=green)

    result = score_transition(left, right)

    assert result.component_scores["spectral"] < 0.5


def test_score_transition_ignores_spectral_component_when_profiles_are_missing() -> None:
    left = track("left", spectral_profile=None)
    right = track("right", spectral_profile=None)

    result = score_transition(left, right)

    assert "spectral" not in result.component_scores


def test_spectral_cohesion_penalizes_different_dominant_colors() -> None:
    red = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    green = SpectralProfile(red_ratio=0.05, green_ratio=0.9, blue_ratio=0.05, dominant_color="GREEN")
    left = track("left", spectral_profile=red)
    right = track("right", spectral_profile=green)

    no_cohesion = score_transition(left, right, config=TransitionScoringConfig(spectral_cohesion=0.0))
    high_cohesion = score_transition(left, right, config=TransitionScoringConfig(spectral_cohesion=1.0))

    assert high_cohesion.total_score < no_cohesion.total_score
    assert "Spectral color penalty applied" in " ".join(high_cohesion.warnings)


def test_spectral_cohesion_boosts_weight_for_same_color() -> None:
    profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    left = track("left", spectral_profile=profile)
    right = track("right", spectral_profile=profile)

    no_cohesion = score_transition(left, right, config=TransitionScoringConfig(spectral_cohesion=0.0))
    high_cohesion = score_transition(left, right, config=TransitionScoringConfig(spectral_cohesion=1.0))

    assert high_cohesion.total_score >= no_cohesion.total_score


def test_spectral_cohesion_out_of_range_is_rejected() -> None:
    with pytest.raises(ValueError):
        TransitionScoringConfig(spectral_cohesion=1.5)

    with pytest.raises(ValueError):
        TransitionScoringConfig(spectral_cohesion=-0.1)
