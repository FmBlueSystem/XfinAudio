"""Deterministic recommendation helpers for XfinAudio."""

from xfinaudio.recommendation.camelot import CamelotKey, parse_camelot_key, score_camelot_transition
from xfinaudio.recommendation.controls import AppliedControls, DJControls, apply_controls
from xfinaudio.recommendation.optimizer import SequenceRecommendation, recommend_sequence
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
from xfinaudio.recommendation.scoring import (
    DEFAULT_SCORING_CONFIG,
    ScoringWeights,
    ThresholdScore,
    TransitionScore,
    TransitionScoringConfig,
    score_transition,
)
from xfinaudio.recommendation.strategies import (
    PlaylistStrategy,
    StrategyRegistry,
    available_strategies,
    default_strategy_registry,
    get_strategy,
)

__all__ = [
    "AppliedControls",
    "CamelotKey",
    "DJControls",
    "PlaylistRecommendation",
    "DEFAULT_SCORING_CONFIG",
    "PlaylistStrategy",
    "ScoringWeights",
    "SequenceRecommendation",
    "StrategyRegistry",
    "ThresholdScore",
    "TransitionScore",
    "TransitionScoringConfig",
    "apply_controls",
    "available_strategies",
    "default_strategy_registry",
    "get_strategy",
    "parse_camelot_key",
    "recommend_playlist",
    "recommend_sequence",
    "score_camelot_transition",
    "score_transition",
]
