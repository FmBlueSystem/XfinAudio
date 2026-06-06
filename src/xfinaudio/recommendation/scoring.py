"""Transparent deterministic transition scoring for TrackRecord pairs."""

from __future__ import annotations

from collections.abc import Collection
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.camelot import BoostRule, score_camelot_transition, shift_camelot_key


class ScoringWeights(BaseModel):
    """Relative component weights for transition scoring."""

    model_config = ConfigDict(frozen=True)

    harmonic: float = 0.40
    bpm: float = 0.25
    energy: float = 0.25
    tags: float = 0.10

    @model_validator(mode="after")
    def validate_weights(self) -> ScoringWeights:
        """Ensure weights are non-negative and at least one component is enabled."""
        if any(weight < 0 for weight in (self.harmonic, self.bpm, self.energy, self.tags)):
            raise ValueError("component weights cannot be negative")
        if self.harmonic + self.bpm + self.energy + self.tags <= 0:
            raise ValueError("total weight must be greater than zero")
        return self


class TransitionScore(BaseModel):
    """Score and human-readable explanation for a track transition."""

    model_config = ConfigDict(frozen=True)

    left_path: str
    right_path: str
    total_score: float
    component_scores: dict[str, float]
    explanations: list[str]
    warnings: list[str]


class ThresholdScore(BaseModel):
    """Score returned when a numeric transition delta is within a threshold."""

    model_config = ConfigDict(frozen=True)

    max_delta: float = Field(ge=0.0)
    score: float = Field(ge=0.0, le=1.0)


class KeyShiftConfig(BaseModel):
    """Optional chromatic key shifts applied only while scoring a transition."""

    model_config = ConfigDict(frozen=True)

    left_semitones: int = 0
    right_semitones: int = 0


class TransitionScoringConfig(BaseModel):
    """Configurable scoring policy with defaults matching existing behavior."""

    model_config = ConfigDict(frozen=True)

    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    bpm_thresholds: tuple[ThresholdScore, ...] = (
        ThresholdScore(max_delta=2.0, score=1.0),
        ThresholdScore(max_delta=4.0, score=0.75),
        ThresholdScore(max_delta=8.0, score=0.5),
    )
    energy_thresholds: tuple[ThresholdScore, ...] = (
        ThresholdScore(max_delta=1.0, score=1.0),
        ThresholdScore(max_delta=2.0, score=0.7),
        ThresholdScore(max_delta=3.0, score=0.4),
    )
    required_fields: tuple[str, ...] = ("camelot_key", "bpm", "energy_level")
    score_curve: Literal["threshold", "fuzzy"] = "threshold"
    key_shift: KeyShiftConfig = Field(default_factory=KeyShiftConfig)


DEFAULT_WEIGHTS = ScoringWeights()
DEFAULT_SCORING_CONFIG = TransitionScoringConfig(weights=DEFAULT_WEIGHTS, score_curve="fuzzy")
REQUIRED_FIELDS = DEFAULT_SCORING_CONFIG.required_fields


def score_transition(
    left: TrackRecord,
    right: TrackRecord,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    boost_rules: Collection[BoostRule] | None = None,
    config: TransitionScoringConfig | None = None,
) -> TransitionScore:
    """Score the musical compatibility from one track to the next."""
    scoring_config = config or DEFAULT_SCORING_CONFIG
    effective_weights = scoring_config.weights if config is not None and weights == DEFAULT_WEIGHTS else weights
    warnings = _metadata_warnings(left, right, scoring_config.required_fields)
    if warnings:
        return TransitionScore(
            left_path=left.path,
            right_path=right.path,
            total_score=0.0,
            component_scores={},
            explanations=[],
            warnings=warnings,
        )

    try:
        left_key = _shifted_key(left.camelot_key or "", scoring_config.key_shift.left_semitones)
        right_key = _shifted_key(right.camelot_key or "", scoring_config.key_shift.right_semitones)
        harmonic_score = score_camelot_transition(left_key, right_key, boost_rules)
    except ValueError:
        return TransitionScore(
            left_path=left.path,
            right_path=right.path,
            total_score=0.0,
            component_scores={},
            explanations=[],
            warnings=_invalid_camelot_warnings(left, right),
        )

    component_scores = {
        "harmonic": harmonic_score,
        "bpm": _score_bpm(left.bpm or 0.0, right.bpm or 0.0, scoring_config),
        "energy": _score_energy(left.energy_level or 0, right.energy_level or 0, scoring_config),
    }
    explanations = [
        f"Harmonic compatibility score is {component_scores['harmonic']:.2f}",
        f"BPM difference is {_bpm_difference_percent(left.bpm or 0.0, right.bpm or 0.0):.2f}%",
        f"Energy level difference is {abs((left.energy_level or 0) - (right.energy_level or 0))}",
    ]
    explanations.extend(
        _key_shift_explanations(
            left.camelot_key or "",
            right.camelot_key or "",
            left_key,
            right_key,
            scoring_config.key_shift,
        )
    )

    tag_score = _score_tags(left, right)
    if tag_score is None:
        warnings.append("Tag score unavailable; both tracks have no tags or genre")
    else:
        component_scores["tags"] = tag_score[0]
        explanations.append(f"Tag overlap is {tag_score[1]}/{tag_score[2]}")
        if tag_score[1] == 0:
            warnings.append("Genre/tag mismatch: no shared genre, subgenre, mood, or tag metadata")

    total_score = _weighted_total(component_scores, effective_weights)
    return TransitionScore(
        left_path=left.path,
        right_path=right.path,
        total_score=round(total_score, 6),
        component_scores=component_scores,
        explanations=explanations,
        warnings=warnings,
    )


def _metadata_warnings(left: TrackRecord, right: TrackRecord, required_fields: tuple[str, ...]) -> list[str]:
    warnings: list[str] = []
    for label, track in (("left", left), ("right", right)):
        missing = [field for field in required_fields if getattr(track, field) is None]
        if missing:
            warnings.append(f"{label} missing required metadata: {', '.join(missing)}")
    return warnings


def _invalid_camelot_warnings(left: TrackRecord, right: TrackRecord) -> list[str]:
    warnings: list[str] = []
    for label, track in (("left", left), ("right", right)):
        if track.camelot_key is not None:
            try:
                score_camelot_transition(track.camelot_key, track.camelot_key)
            except ValueError:
                warnings.append(f"{label} has invalid Camelot key: {track.camelot_key}")
    return warnings or ["invalid Camelot key"]


def _bpm_difference_percent(left_bpm: float, right_bpm: float) -> float:
    lower = min(left_bpm, right_bpm)
    if lower <= 0:
        return 100.0
    return abs(left_bpm - right_bpm) / lower * 100


def _shifted_key(camelot_key: str, semitones: int) -> str:
    return shift_camelot_key(camelot_key, semitones)


def _key_shift_explanations(
    left_original: str,
    right_original: str,
    left_effective: str,
    right_effective: str,
    key_shift: KeyShiftConfig,
) -> list[str]:
    explanations: list[str] = []
    if key_shift.left_semitones:
        explanations.append(f"Pitch/key normalization shifted left key from {left_original} to {left_effective}")
    if key_shift.right_semitones:
        explanations.append(f"Pitch/key normalization shifted right key from {right_original} to {right_effective}")
    return explanations


def _score_bpm(left_bpm: float, right_bpm: float, config: TransitionScoringConfig) -> float:
    delta = _bpm_difference_percent(left_bpm, right_bpm)
    if config.score_curve == "fuzzy":
        return _score_fuzzy(delta, config.bpm_thresholds)
    return _score_threshold(delta, config.bpm_thresholds)


def _score_energy(left_energy: int, right_energy: int, config: TransitionScoringConfig) -> float:
    delta = float(abs(left_energy - right_energy))
    if config.score_curve == "fuzzy":
        return _score_fuzzy(delta, config.energy_thresholds)
    return _score_threshold(delta, config.energy_thresholds)


def _score_fuzzy(delta: float, thresholds: tuple[ThresholdScore, ...]) -> float:
    max_delta = max((threshold.max_delta for threshold in thresholds), default=0.0)
    if max_delta <= 0:
        return 0.0
    normalized = min(max(delta / max_delta, 0.0), 1.0)
    return round(1.0 - normalized**2, 6)


def _score_threshold(delta: float, thresholds: tuple[ThresholdScore, ...]) -> float:
    for threshold in sorted(thresholds, key=lambda candidate: candidate.max_delta):
        if delta <= threshold.max_delta:
            return threshold.score
    return 0.0


def _score_tags(left: TrackRecord, right: TrackRecord) -> tuple[float, int, int] | None:
    left_tags = _normalized_tags(left)
    right_tags = _normalized_tags(right)
    union = left_tags | right_tags
    if not union:
        return None
    overlap = left_tags & right_tags
    return len(overlap) / len(union), len(overlap), len(union)


def _normalized_tags(track: TrackRecord) -> set[str]:
    values = [*track.tags]
    if track.genre:
        values.append(track.genre)
    return {value.strip().casefold() for value in values if value.strip()}


def _weighted_total(component_scores: dict[str, float], weights: ScoringWeights) -> float:
    available_weights = {name: getattr(weights, name) for name in component_scores}
    total_weight = sum(available_weights.values())
    if total_weight <= 0:
        return 0.0
    return sum(component_scores[name] * weight for name, weight in available_weights.items()) / total_weight
