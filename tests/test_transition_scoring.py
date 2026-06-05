import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.scoring import ScoringWeights, ThresholdScore, TransitionScoringConfig, score_transition


def track(
    path: str,
    *,
    bpm: float | None = 120.0,
    camelot_key: str | None = "8A",
    energy_level: int | None = 5,
    genre: str | None = "House",
    tags: list[str] | None = None,
    missing_required_fields: list[str] | None = None,
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
    )


def test_score_transition_scores_bpm_compatibility() -> None:
    result = score_transition(track("left", bpm=120.0), track("right", bpm=123.0))

    assert result.component_scores["bpm"] == 0.75
    assert "BPM difference is 2.50%" in result.explanations


def test_score_transition_scores_energy_compatibility() -> None:
    result = score_transition(track("left", energy_level=4), track("right", energy_level=6))

    assert result.component_scores["energy"] == 0.7
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

    assert result.total_score == pytest.approx(0.8125)
    assert result.component_scores == {"harmonic": 1.0, "bpm": 0.75, "energy": 0.7, "tags": 0.5}


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
        ScoringWeights(harmonic=0.0, bpm=0.0, energy=0.0, tags=0.0)


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
