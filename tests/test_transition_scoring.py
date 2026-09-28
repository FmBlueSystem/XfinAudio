import pytest

from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.spectral_profile import (
    EdgeSpectralProfile,
    SpectralProfile,
    dominant_color_for_ratios,
    score_spectral_similarity,
)
from xfinaudio.audio.tonal_profile import TonalProfile
from xfinaudio.config.settings import AppSettings
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import recommend_playlist
from xfinaudio.recommendation.scoring import (
    COMPATIBILITY_COMPONENTS,
    MIXABILITY_COMPONENTS,
    NEUTRAL_COMPONENT_SCORE,
    SCORED_COMPONENTS,
    KeyShiftConfig,
    ScoringWeights,
    ThresholdScore,
    TransitionScore,
    TransitionScoringConfig,
    _bpm_difference_percent,
    _effective_energy_delta,
    bpm_difference_percent,
    effective_energy_delta,
    normalized_bpm_pair,
    score_transition,
)
from xfinaudio.recommendation.strategies import default_strategy_registry


def track(
    path: str,
    *,
    bpm: float | None = 120.0,
    camelot_key: str | None = "8A",
    energy_level: int | None = 5,
    energy_in: int | None = None,
    energy_out: int | None = None,
    energy_peak: int | None = None,
    genre: str | None = "House",
    tags: list[str] | None = None,
    missing_required_fields: list[str] | None = None,
    spectral_profile: SpectralProfile | None = None,
    danceability_profile: DanceabilityProfile | None = None,
    edge_spectral_profile: EdgeSpectralProfile | None = None,
    tonal_profile: TonalProfile | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        energy_in=energy_in,
        energy_out=energy_out,
        energy_peak=energy_peak,
        genre=genre,
        tags=["Peak", "Vocal"] if tags is None else tags,
        metadata_status="complete" if missing_required_fields is None else "incomplete",
        missing_required_fields=missing_required_fields or [],
        spectral_profile=spectral_profile,
        danceability_profile=danceability_profile,
        edge_spectral_profile=edge_spectral_profile,
        tonal_profile=tonal_profile,
    )


def danceability(score: float) -> DanceabilityProfile:
    return DanceabilityProfile(
        score=score,
        pulse_clarity=score,
        tempo_confidence=score,
        percussive_ratio=score,
    )


def spectral(red: float, green: float, blue: float, color: str) -> SpectralProfile:
    return SpectralProfile(
        red_ratio=red,
        green_ratio=green,
        blue_ratio=blue,
        dominant_color=color,  # type: ignore[arg-type]
    )


def test_score_transition_scores_bpm_compatibility() -> None:
    result = score_transition(track("left", bpm=120.0), track("right", bpm=123.0))

    assert result.component_scores["bpm"] == pytest.approx(0.902344)
    assert "BPM difference is 2.50%" in result.explanations


def test_score_transition_explanation_reports_zero_percent_for_half_time_pair() -> None:
    result = score_transition(track("left", bpm=128.0), track("right", bpm=64.0))

    assert "BPM difference is 0.00%" in result.explanations


def test_score_transition_scores_energy_compatibility() -> None:
    result = score_transition(track("left", energy_level=4), track("right", energy_level=6))

    assert result.component_scores["energy"] == pytest.approx(0.555556)
    assert "Energy level difference is 2" in result.explanations


def test_score_transition_uses_out_to_in_energy_handoff_when_both_are_available() -> None:
    result = score_transition(
        track("left", energy_level=4, energy_out=8),
        track("right", energy_level=8, energy_in=8),
    )

    assert result.component_scores["energy"] == 1.0
    assert "Energy handoff (out→in) difference is 0" in result.explanations


def test_effective_energy_delta_returns_handoff_delta_and_usage() -> None:
    result = effective_energy_delta(
        track("left", energy_level=4, energy_out=8),
        track("right", energy_level=8, energy_in=8),
    )

    assert result == (0.0, True)


def test_private_effective_energy_delta_is_public_helper_alias() -> None:
    assert _effective_energy_delta is effective_energy_delta


def test_score_transition_falls_back_to_scalar_energy_when_one_handoff_side_is_missing() -> None:
    result = score_transition(
        track("left", energy_level=4, energy_out=8),
        track("right", energy_level=8),
    )

    assert result.component_scores["energy"] == 0.0
    assert "Energy level difference is 4" in result.explanations
    assert not any("Energy handoff" in explanation for explanation in result.explanations)


def test_score_transition_scores_tag_overlap_with_genre() -> None:
    left = track("left", genre="House", tags=["Peak", "Vocal"])
    right = track("right", genre="House", tags=["Peak", "Deep"])

    result = score_transition(left, right)

    assert result.component_scores["tags"] == pytest.approx(0.5)
    assert "Tag overlap is 2/4" in result.explanations


def test_score_transition_scores_missing_tags_as_neutral_not_perfect() -> None:
    """An unevaluable component must not be treated as agreement.

    Excluding it from the denominator inflated the total, so pairs with less
    metadata outranked fully-described ones. Absent components score neutral.
    """
    left = track("left", genre=None, tags=[])
    right = track("right", genre=None, tags=[])

    result = score_transition(left, right)

    assert "tags" not in result.component_scores
    assert result.total_score < 1.0
    assert "Tag score unavailable; both tracks have no tags or genre" in result.warnings


def test_sparse_metadata_pair_does_not_outrank_complete_agreeing_pair() -> None:
    """The optimizer must never prefer a track just because it is undocumented."""
    red = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    complete_left = track("cl", genre="House", tags=["Peak"], spectral_profile=red)
    complete_right = track("cr", genre="House", tags=["Peak"], spectral_profile=red)
    sparse_left = track("sl", genre=None, tags=[], spectral_profile=None)
    sparse_right = track("sr", genre=None, tags=[], spectral_profile=None)

    complete = score_transition(complete_left, complete_right)
    sparse = score_transition(sparse_left, sparse_right)

    assert sparse.total_score < complete.total_score


def test_absent_component_scores_between_disagreement_and_agreement() -> None:
    """Neutral must sit between a known mismatch and a known match."""
    agreeing = score_transition(track("al", genre="House", tags=["Peak"]), track("ar", genre="House", tags=["Peak"]))
    unknown = score_transition(track("ul", genre=None, tags=[]), track("ur", genre=None, tags=[]))
    clashing = score_transition(track("cl", genre="Techno", tags=["Dark"]), track("cr", genre="Disco", tags=["Happy"]))

    assert clashing.total_score < unknown.total_score < agreeing.total_score


def test_score_transition_warns_and_returns_zero_when_required_metadata_is_incomplete() -> None:
    result = score_transition(
        track("left", camelot_key=None, missing_required_fields=["camelot_key"]),
        track("right"),
    )

    assert result.total_score == 0.0
    assert result.compatibility_score is None
    assert result.mixability_score is None
    assert "left missing required metadata: camelot_key" in result.warnings


def test_score_transition_combines_weighted_component_scores() -> None:
    left = track("left", bpm=120.0, camelot_key="8A", energy_level=4, genre="House", tags=["Peak", "Vocal"])
    right = track("right", bpm=123.0, camelot_key="8A", energy_level=6, genre="House", tags=["Peak", "Deep"])

    result = score_transition(left, right)

    # (0.4 + 0.902344*0.25 + 0.555556*0.25 + 0.5*0.1 + 0.5*0.1) / 1.10, where the
    # trailing 0.5 is the neutral score for the absent spectral component.
    assert result.total_score == pytest.approx(0.785886)
    expected_compatibility = (1.0 * 0.40 + 0.5 * 0.10 + 0.5 * 0.0 + 0.5 * 0.10) / (0.40 + 0.10 + 0.0 + 0.10)
    expected_mixability = (0.902344 * 0.25 + 0.555556 * 0.25) / (0.25 + 0.25)
    assert result.compatibility_score == pytest.approx(expected_compatibility)
    assert result.mixability_score == pytest.approx(expected_mixability)
    # component_scores still reports only what could actually be measured.
    assert result.component_scores == {
        "harmonic": 1.0,
        "bpm": pytest.approx(0.902344),
        "energy": pytest.approx(0.555556),
        "tags": 0.5,
    }


def test_score_transition_splits_fully_populated_pair_into_informative_axes() -> None:
    profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    weights = ScoringWeights(danceability=0.2)
    left = track(
        "left",
        bpm=120.0,
        energy_level=4,
        tags=["Peak", "Vocal"],
        spectral_profile=profile,
        danceability_profile=danceability(0.8),
    )
    right = track(
        "right",
        bpm=123.0,
        energy_level=6,
        tags=["Peak", "Deep"],
        spectral_profile=profile,
        danceability_profile=danceability(0.3),
    )

    result = score_transition(left, right, weights=weights)

    expected_compatibility = (1.0 * 0.40 + 0.5 * 0.10 + 0.5 * 0.20 + 1.0 * 0.10) / (0.40 + 0.10 + 0.20 + 0.10)
    expected_mixability = (0.902344 * 0.25 + 0.555556 * 0.25) / (0.25 + 0.25)
    assert result.compatibility_score == pytest.approx(expected_compatibility)
    assert result.mixability_score == pytest.approx(expected_mixability)
    assert result.total_score == pytest.approx(0.780365)


def test_score_transition_warns_and_returns_zero_for_invalid_camelot_key() -> None:
    result = score_transition(track("left", camelot_key="not-a-key"), track("right"))

    assert result.total_score == 0.0
    assert result.compatibility_score is None
    assert result.mixability_score is None
    assert "left has invalid Camelot key: not-a-key" in result.warnings


def test_transition_score_axes_default_to_none_for_existing_constructors() -> None:
    score = TransitionScore(
        left_path="left",
        right_path="right",
        total_score=0.5,
        component_scores={"harmonic": 0.5},
        explanations=[],
        warnings=[],
    )

    assert score.compatibility_score is None
    assert score.mixability_score is None


def test_transition_score_axis_components_partition_all_scored_components() -> None:
    compatibility = set(COMPATIBILITY_COMPONENTS)
    mixability = set(MIXABILITY_COMPONENTS)

    assert compatibility.isdisjoint(mixability)
    assert compatibility | mixability == set(SCORED_COMPONENTS)
    assert "spectral_edge" in MIXABILITY_COMPONENTS


def test_edge_spectral_score_compares_left_outro_to_right_intro() -> None:
    red = spectral(0.9, 0.05, 0.05, "RED")
    green = spectral(0.05, 0.9, 0.05, "GREEN")
    blue = spectral(0.05, 0.05, 0.9, "BLUE")
    left_edge = EdgeSpectralProfile(intro=red, outro=green)
    right_edge = EdgeSpectralProfile(intro=blue, outro=red)
    weights = ScoringWeights(spectral_edge=0.2)

    result = score_transition(
        track("left", edge_spectral_profile=left_edge),
        track("right", edge_spectral_profile=right_edge),
        weights=weights,
    )

    assert result.component_scores["spectral_edge"] == score_spectral_similarity(left_edge.outro, right_edge.intro)


def test_edge_spectral_score_is_directional() -> None:
    red = spectral(0.9, 0.05, 0.05, "RED")
    green = spectral(0.05, 0.9, 0.05, "GREEN")
    blue = spectral(0.05, 0.05, 0.9, "BLUE")
    left = track("left", edge_spectral_profile=EdgeSpectralProfile(intro=red, outro=green))
    right = track("right", edge_spectral_profile=EdgeSpectralProfile(intro=blue, outro=red))
    weights = ScoringWeights(spectral_edge=0.2)

    forward = score_transition(left, right, weights=weights)
    reverse = score_transition(right, left, weights=weights)

    assert forward.component_scores["spectral_edge"] != reverse.component_scores["spectral_edge"]


@pytest.mark.parametrize("missing_side", ["left", "right"])
def test_missing_edge_profile_is_absent_and_scores_neutral(missing_side: str) -> None:
    red = spectral(0.9, 0.05, 0.05, "RED")
    edge = EdgeSpectralProfile(intro=red, outro=red)
    left = track("left", edge_spectral_profile=None if missing_side == "left" else edge)
    right = track("right", edge_spectral_profile=None if missing_side == "right" else edge)
    weights = ScoringWeights(
        harmonic=0.0,
        bpm=0.0,
        energy=0.0,
        tags=0.0,
        spectral=0.0,
        danceability=0.0,
        spectral_edge=0.2,
    )

    result = score_transition(left, right, weights=weights)

    assert "spectral_edge" not in result.component_scores
    assert result.total_score == 0.5


def test_edge_spectral_default_weight_is_disabled() -> None:
    assert ScoringWeights().spectral_edge == 0.0


def test_transition_score_axis_is_none_when_all_its_weights_are_zero() -> None:
    compatibility_disabled = ScoringWeights(
        harmonic=0.0,
        bpm=0.5,
        energy=0.5,
        tags=0.0,
        spectral=0.0,
        danceability=0.0,
    )
    mixability_disabled = ScoringWeights(
        harmonic=0.5,
        bpm=0.0,
        energy=0.0,
        tags=0.5,
        spectral=0.0,
        danceability=0.0,
    )

    compatibility_none = score_transition(track("left-c"), track("right-c"), weights=compatibility_disabled)
    mixability_none = score_transition(track("left-m"), track("right-m"), weights=mixability_disabled)

    assert compatibility_none.compatibility_score is None
    assert compatibility_none.mixability_score is not None
    assert mixability_none.compatibility_score is not None
    assert mixability_none.mixability_score is None


def test_score_transition_accepts_controlled_boost_rules() -> None:
    result = score_transition(
        track("left", camelot_key="8A"), track("right", camelot_key="10A"), boost_rules={("8A", "10A")}
    )

    assert result.component_scores["harmonic"] == 0.8


def test_scoring_weights_reject_non_positive_total_weight() -> None:
    with pytest.raises(ValueError, match="total weight must be greater than zero"):
        ScoringWeights(harmonic=0.0, bpm=0.0, energy=0.0, tags=0.0, spectral=0.0, danceability=0.0)


def test_scoring_weights_reject_negative_component_weights() -> None:
    with pytest.raises(ValueError, match="component weights cannot be negative"):
        ScoringWeights(harmonic=1.0, bpm=0.0, energy=0.0, tags=0.0, spectral=0.0, danceability=-0.1)


def test_score_transition_scores_danceability_and_includes_it_in_total() -> None:
    weights = ScoringWeights(harmonic=0.0, bpm=0.0, energy=0.0, tags=0.0, spectral=0.0, danceability=0.2)
    left = track("left", danceability_profile=danceability(0.8))
    right = track("right", danceability_profile=danceability(0.3))

    result = score_transition(left, right, weights=weights)

    assert result.component_scores["danceability"] == pytest.approx(0.5)
    assert result.total_score == pytest.approx(0.5)
    assert "Danceability similarity is 0.50" in result.explanations


def test_absent_danceability_scores_between_clash_and_match() -> None:
    weights = ScoringWeights(harmonic=0.0, bpm=0.0, energy=0.0, tags=0.0, spectral=0.0, danceability=0.2)
    clashing = score_transition(
        track("cl", danceability_profile=danceability(0.0)),
        track("cr", danceability_profile=danceability(1.0)),
        weights=weights,
    )
    unknown = score_transition(
        track("ul", danceability_profile=danceability(0.5)),
        track("ur"),
        weights=weights,
    )
    matching = score_transition(
        track("ml", danceability_profile=danceability(0.7)),
        track("mr", danceability_profile=danceability(0.7)),
        weights=weights,
    )

    assert "danceability" not in unknown.component_scores
    assert clashing.total_score < unknown.total_score < matching.total_score


def test_score_transition_distinguishes_omitted_weights_from_explicit_defaults() -> None:
    config = TransitionScoringConfig(weights=ScoringWeights(harmonic=0.0, bpm=0.0, energy=1.0, tags=0.0, spectral=0.0))
    left = track("left", energy_level=4)
    right = track("right", energy_level=6)

    implicit = score_transition(left, right, config=config)
    explicit = score_transition(left, right, weights=ScoringWeights(), config=config)

    assert implicit.total_score == implicit.component_scores["energy"]
    assert explicit.total_score != implicit.total_score


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
    # 8A -> 1A is a genuine clash. The original pair here was 8A -> 6A, which is
    # +2 on the same ring and now scores as an Energy Boost rather than 0.
    result = score_transition(track("left", camelot_key="8A"), track("right", camelot_key="1A"))

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
    expected_compatibility = (
        high_cohesion.component_scores["harmonic"] * 0.40
        + high_cohesion.component_scores["tags"] * 0.10
        + 0.5 * 0.0
        + high_cohesion.component_scores["spectral"] * 0.20
    ) / (0.40 + 0.10 + 0.0 + 0.20)
    assert high_cohesion.compatibility_score == pytest.approx(expected_compatibility)
    assert "Spectral color penalty applied" in " ".join(high_cohesion.warnings)


def test_spectral_cohesion_boosts_weight_for_same_color() -> None:
    profile = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    left = track("left", spectral_profile=profile)
    right = track("right", spectral_profile=profile)

    no_cohesion = score_transition(left, right, config=TransitionScoringConfig(spectral_cohesion=0.0))
    high_cohesion = score_transition(left, right, config=TransitionScoringConfig(spectral_cohesion=1.0))

    assert high_cohesion.total_score >= no_cohesion.total_score


def test_new_color_rule_drives_spectral_penalty_for_different_and_same_colors() -> None:
    red = SpectralProfile(
        red_ratio=0.46,
        green_ratio=0.40,
        blue_ratio=0.14,
        dominant_color=dominant_color_for_ratios(0.46, 0.40, 0.14),
    )
    blue = SpectralProfile(
        red_ratio=0.40,
        green_ratio=0.35,
        blue_ratio=0.25,
        dominant_color=dominant_color_for_ratios(0.40, 0.35, 0.25),
    )
    config = TransitionScoringConfig(spectral_cohesion=0.5)

    different = score_transition(
        track("red", spectral_profile=red), track("blue", spectral_profile=blue), config=config
    )
    same = score_transition(track("red-1", spectral_profile=red), track("red-2", spectral_profile=red), config=config)

    assert "Spectral color penalty applied" in " ".join(different.warnings)
    assert "Spectral color penalty applied" not in " ".join(same.warnings)


def test_default_app_settings_drive_new_color_penalty_through_recommendation() -> None:
    settings = AppSettings()
    red = SpectralProfile(
        red_ratio=0.46,
        green_ratio=0.40,
        blue_ratio=0.14,
        dominant_color=dominant_color_for_ratios(0.46, 0.40, 0.14),
    )
    blue = SpectralProfile(
        red_ratio=0.40,
        green_ratio=0.35,
        blue_ratio=0.25,
        dominant_color=dominant_color_for_ratios(0.40, 0.35, 0.25),
    )

    different = recommend_playlist(
        [track("red", spectral_profile=red), track("blue", spectral_profile=blue)],
        "build",
        spectral_cohesion=settings.scoring.spectral_cohesion,
    )
    same = recommend_playlist(
        [track("red-1", spectral_profile=red), track("red-2", spectral_profile=red)],
        "build",
        spectral_cohesion=settings.scoring.spectral_cohesion,
    )

    assert "Spectral color penalty applied" in " ".join(different.transition_scores[0].warnings)
    assert "Spectral color penalty applied" not in " ".join(same.transition_scores[0].warnings)


def test_spectral_cohesion_out_of_range_is_rejected() -> None:
    with pytest.raises(ValueError):
        TransitionScoringConfig(spectral_cohesion=1.5)

    with pytest.raises(ValueError):
        TransitionScoringConfig(spectral_cohesion=-0.1)


def test_bpm_difference_percent_treats_exact_double_time_pairs_as_compatible() -> None:
    assert _bpm_difference_percent(128.0, 64.0) == pytest.approx(0.0, abs=1e-6)
    assert _bpm_difference_percent(64.0, 128.0) == pytest.approx(0.0, abs=1e-6)


def test_public_bpm_difference_percent_normalizes_near_double_time_pair() -> None:
    assert bpm_difference_percent(84.6, 169.0) < 1.0


def test_normalized_bpm_pair_folds_double_time_and_preserves_non_double_time() -> None:
    assert normalized_bpm_pair(128.0, 64.0) == (64.0, 64.0)
    assert normalized_bpm_pair(100.0, 130.0) == (100.0, 130.0)


def test_private_bpm_difference_percent_is_backward_compatible_alias() -> None:
    assert _bpm_difference_percent is bpm_difference_percent


def test_bpm_difference_percent_non_half_time_pair_is_unaffected() -> None:
    assert _bpm_difference_percent(128.0, 100.0) == pytest.approx(28.0, abs=0.01)
    assert _bpm_difference_percent(100.0, 128.0) == pytest.approx(28.0, abs=0.01)


def test_bpm_difference_percent_tolerance_boundary_inside_band_is_near_zero() -> None:
    # ratio = 128 / 64.97 ~= 1.9698, inside [1.96, 2.04] -> normalized to near-zero.
    assert _bpm_difference_percent(128.0, 64.97) < 5.0
    assert _bpm_difference_percent(64.97, 128.0) < 5.0


def test_bpm_difference_percent_tolerance_boundary_outside_band_falls_back_to_plain_formula() -> None:
    # ratio = 128 / 65.64 ~= 1.9500, outside [1.96, 2.04] -> plain formula, ~95% difference.
    assert _bpm_difference_percent(128.0, 65.64) > 50.0
    assert _bpm_difference_percent(65.64, 128.0) > 50.0


def test_energy_boost_transition_explains_that_it_needs_a_cut() -> None:
    """A +2 lift is playable but clashes if the two keys overlap.

    The DJ has to know to cut rather than run a long blend, so the transition
    says so instead of silently scoring 0.70.
    """
    result = score_transition(track("left", camelot_key="8A"), track("right", camelot_key="10A"))

    assert any("cut" in explanation.lower() for explanation in result.explanations), result.explanations


def test_ordinary_harmonic_transition_says_nothing_about_cutting() -> None:
    result = score_transition(track("left", camelot_key="8A"), track("right", camelot_key="9A"))

    assert not any("cut" in explanation.lower() for explanation in result.explanations)


# ---------------------------------------------------------------------------
# Familiarity preference weight (Plan 3 T3) — declared on ScoringWeights,
# consumed at the candidate-pool seam, inert in transition scoring.
# ---------------------------------------------------------------------------


def test_familiarity_weight_defaults_to_inert_zero() -> None:
    assert ScoringWeights().familiarity == 0.0


def test_familiarity_weight_is_not_a_transition_component() -> None:
    """Familiarity is per-track, not a transition-pair component.

    Transition totals normalize by the sum of SCORED_COMPONENTS weights; the
    familiarity weight must stay outside that set so the normalization (and
    every transition score) is byte-identical whether the weight is 0.0 or set.
    """
    assert "familiarity" not in SCORED_COMPONENTS


def test_familiarity_weight_does_not_change_transition_scores() -> None:
    left = track("left", bpm=120.0, energy_level=4, tags=["Peak", "Vocal"])
    right = track("right", bpm=123.0, energy_level=6, tags=["Peak", "Deep"])
    baseline = score_transition(left, right, weights=ScoringWeights())
    with_weight = score_transition(left, right, weights=ScoringWeights(familiarity=0.3))

    assert with_weight.total_score == baseline.total_score
    assert with_weight.compatibility_score == baseline.compatibility_score
    assert with_weight.mixability_score == baseline.mixability_score
    assert with_weight.component_scores == baseline.component_scores


def test_familiarity_weight_reject_negative_values() -> None:
    with pytest.raises(ValueError, match="component weights cannot be negative"):
        ScoringWeights(familiarity=-0.1)


# ---------------------------------------------------------------------------
# Tonal interval compatibility weight (Harmonic core v2) — audio-derived TIV
# joins the compatibility axis, disabled by default and inert at 0.0.
# ---------------------------------------------------------------------------


def _tonal(tiv: tuple[float, float, float, float, float, float], *, coherence: float = 0.5) -> TonalProfile:
    return TonalProfile(tiv=tiv, tonal_coherence=coherence)


def _tonal_only_weights(**overrides: float) -> ScoringWeights:
    base = {
        "harmonic": 0.0,
        "bpm": 0.0,
        "energy": 0.0,
        "tags": 0.0,
        "spectral": 0.0,
        "danceability": 0.0,
        "spectral_edge": 0.0,
        "tonal": 1.0,
    }
    base.update(overrides)
    return ScoringWeights(**base)


def test_tonal_default_weight_is_disabled() -> None:
    assert ScoringWeights().tonal == 0.0


def test_tonal_component_joins_the_compatibility_axis() -> None:
    assert "tonal" in SCORED_COMPONENTS
    assert "tonal" in COMPATIBILITY_COMPONENTS
    assert "tonal" not in MIXABILITY_COMPONENTS


def test_every_builtin_strategy_leaves_tonal_disabled() -> None:
    registry = default_strategy_registry()

    enabled = {name for name in registry.available() if registry.get(name).weights.tonal != 0.0}

    assert enabled == set()


def test_tonal_weight_zero_leaves_total_unchanged_with_profiles() -> None:
    without = score_transition(track("left"), track("right"), weights=ScoringWeights())
    with_profiles = score_transition(
        track("left", tonal_profile=_tonal((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))),
        track("right", tonal_profile=_tonal((0.0, 0.0, 0.0, 1.0, 0.0, 0.0))),
        weights=ScoringWeights(),
    )

    # The component is reported when measurable, but its zero weight is inert.
    assert "tonal" in with_profiles.component_scores
    assert with_profiles.total_score == without.total_score
    assert with_profiles.compatibility_score == without.compatibility_score


def test_tonal_weight_affects_total_when_profiles_present() -> None:
    weights = _tonal_only_weights()
    matching = score_transition(
        track("ml", tonal_profile=_tonal((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))),
        track("mr", tonal_profile=_tonal((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))),
        weights=weights,
    )
    differing = score_transition(
        track("dl", tonal_profile=_tonal((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))),
        track("dr", tonal_profile=_tonal((0.0, 0.0, 0.0, 1.0, 0.0, 0.0))),
        weights=weights,
    )

    assert matching.component_scores["tonal"] == pytest.approx(1.0)
    assert differing.component_scores["tonal"] == pytest.approx(0.0)
    assert matching.total_score > differing.total_score
    assert "Tonal compatibility is 1.00" in matching.explanations


def test_absent_tonal_profile_is_absent_and_neutral() -> None:
    result = score_transition(track("left"), track("right"), weights=_tonal_only_weights())

    assert "tonal" not in result.component_scores
    assert result.total_score == 0.5


def test_degenerate_tonal_profile_is_absent_and_neutral() -> None:
    degenerate = _tonal((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    result = score_transition(
        track("left", tonal_profile=degenerate),
        track("right", tonal_profile=degenerate),
        weights=_tonal_only_weights(),
    )

    assert "tonal" not in result.component_scores
    assert result.total_score == 0.5


def test_tonal_compatibility_is_symmetric() -> None:
    weak = _tonal((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    strong = _tonal((0.6, 0.8, 0.0, 0.0, 0.0, 0.0))

    forward = score_transition(
        track("left", tonal_profile=weak), track("right", tonal_profile=strong), weights=_tonal_only_weights()
    )
    reverse = score_transition(
        track("right", tonal_profile=strong), track("left", tonal_profile=weak), weights=_tonal_only_weights()
    )

    assert forward.component_scores["tonal"] == reverse.component_scores["tonal"]


# ---------------------------------------------------------------------------
# Triad/tanda adjacency weight (Engine pack slice 2, T1) — rehearsed-together
# provenance joins the mixability axis, disabled by default and inert at 0.0.
#
# Adjacency/momentum ("can these two be joined right now") is mixability, like
# bpm/energy/spectral_edge; compatibility asks whether two tracks belong in the
# same set, which a shared rehearsal says nothing about.
#
# Absent OR disjoint identities score neutral: a track that is not in a triad,
# and a track that is in a different triad, give the engine no evidence either
# way. Scoring disjoint identities as 0.0 would turn a provenance bonus into a
# penalty on every unrehearsed pair, which is exactly the gate a bonus must
# never become.
# ---------------------------------------------------------------------------


def _triad_only_weights(**overrides: float) -> ScoringWeights:
    base = {
        "harmonic": 0.0,
        "bpm": 0.0,
        "energy": 0.0,
        "tags": 0.0,
        "spectral": 0.0,
        "danceability": 0.0,
        "spectral_edge": 0.0,
        "tonal": 0.0,
        "triad": 1.0,
    }
    base.update(overrides)
    return ScoringWeights(**base)


def test_triad_default_weight_is_disabled() -> None:
    assert ScoringWeights().triad == 0.0


def test_triad_component_joins_the_mixability_axis() -> None:
    assert "triad" in SCORED_COMPONENTS
    assert "triad" in MIXABILITY_COMPONENTS
    assert "triad" not in COMPATIBILITY_COMPONENTS


def test_triad_default_weight_does_not_change_the_normalization_denominator() -> None:
    """Byte-identical totals depend on this sum, so it is pinned explicitly."""
    weights = ScoringWeights()

    assert sum(getattr(weights, name) for name in SCORED_COMPONENTS) == pytest.approx(1.10)


def test_every_builtin_strategy_leaves_triad_disabled() -> None:
    registry = default_strategy_registry()

    enabled = {name for name in registry.available() if registry.get(name).weights.triad != 0.0}

    assert enabled == set()


def test_shared_triad_identity_scores_one_and_joins_the_total() -> None:
    result = score_transition(
        track("left", tags=["triad:a7f3"]),
        track("right", tags=["TRIAD:A7F3"]),
        weights=_triad_only_weights(),
    )

    assert result.component_scores["triad"] == 1.0
    assert result.total_score == pytest.approx(1.0)
    assert result.mixability_score == pytest.approx(1.0)
    assert result.compatibility_score is None
    assert "Rehearsed triad/tanda shared: a7f3" in result.explanations


def test_sharing_any_single_triad_identity_is_enough() -> None:
    result = score_transition(
        track("left", tags=["triad:alpha", "triad:bravo"]),
        track("right", tags=["triad:bravo", "triad:charlie"]),
        weights=_triad_only_weights(),
    )

    assert result.component_scores["triad"] == 1.0


def test_triad_component_is_symmetric() -> None:
    left = track("left", tags=["triad:alpha", "triad:bravo"])
    right = track("right", tags=["triad:BRAVO"])

    forward = score_transition(left, right, weights=_triad_only_weights())
    reverse = score_transition(right, left, weights=_triad_only_weights())

    assert forward.component_scores["triad"] == reverse.component_scores["triad"] == 1.0


def test_shared_triad_identity_is_reported_even_at_zero_weight() -> None:
    result = score_transition(track("left", tags=["triad:a7f3"]), track("right", tags=["triad:a7f3"]))

    assert result.component_scores["triad"] == 1.0


def test_absent_or_disjoint_triad_identities_are_neutral_and_never_penalized() -> None:
    weights = _triad_only_weights()
    shared = score_transition(
        track("sl", tags=["triad:a7f3"]), track("sr", tags=["triad:a7f3"]), weights=weights
    )
    absent = score_transition(track("al", tags=[]), track("ar", tags=[]), weights=weights)
    one_sided = score_transition(track("ol", tags=["triad:a7f3"]), track("or", tags=[]), weights=weights)
    disjoint = score_transition(
        track("dl", tags=["triad:a7f3"]), track("dr", tags=["triad:9c21"]), weights=weights
    )

    assert "triad" not in absent.component_scores
    assert "triad" not in one_sided.component_scores
    assert "triad" not in disjoint.component_scores
    assert absent.total_score == NEUTRAL_COMPONENT_SCORE
    assert one_sided.total_score == NEUTRAL_COMPONENT_SCORE
    assert disjoint.total_score == NEUTRAL_COMPONENT_SCORE
    # A bonus, never a gate: the rehearsed pair outranks the unrehearsed ones,
    # and being in a DIFFERENT triad costs exactly as much as being in none.
    assert shared.total_score > disjoint.total_score == absent.total_score


def test_triad_weight_raises_the_total_above_the_same_pair_without_the_bonus() -> None:
    """The opt-in knob, isolated: the tonal weight keeps the weight sum valid.

    Tonal profiles are absent here, so the tonal component stays neutral and the
    ONLY difference between the arms is the triad weight.
    """
    left = track("left", tags=["Peak", "triad:a7f3"])
    right = track("right", tags=["Peak", "triad:a7f3"])
    base = _triad_only_weights(tonal=0.5, triad=0.0)
    with_triad = base.model_copy(update={"triad": 0.5})

    without = score_transition(left, right, weights=base)
    with_bonus = score_transition(left, right, weights=with_triad)

    assert without.total_score == NEUTRAL_COMPONENT_SCORE
    assert without.mixability_score is None
    assert with_bonus.total_score > without.total_score
    assert with_bonus.mixability_score == pytest.approx(1.0)
