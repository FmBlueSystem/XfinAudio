"""Deterministic recommendation helpers for XfinAudio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xfinaudio.recommendation.camelot import CamelotKey, parse_camelot_key, score_camelot_transition
    from xfinaudio.recommendation.controls import AppliedControls, DJControls, apply_controls
    from xfinaudio.recommendation.optimizer import SequenceRecommendation, recommend_sequence
    from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
    from xfinaudio.recommendation.prep_copilot import (
        DJSetIntent,
        PrepCopilotPlan,
        PrepCopilotVariant,
        PrepVariantName,
        build_prep_copilot_plan,
    )
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

_EXPORTS: dict[str, tuple[str, str]] = {
    "AppliedControls": ("xfinaudio.recommendation.controls", "AppliedControls"),
    "CamelotKey": ("xfinaudio.recommendation.camelot", "CamelotKey"),
    "DJControls": ("xfinaudio.recommendation.controls", "DJControls"),
    "DJSetIntent": ("xfinaudio.recommendation.prep_copilot", "DJSetIntent"),
    "PlaylistRecommendation": ("xfinaudio.recommendation.playlist_service", "PlaylistRecommendation"),
    "PrepCopilotPlan": ("xfinaudio.recommendation.prep_copilot", "PrepCopilotPlan"),
    "PrepCopilotVariant": ("xfinaudio.recommendation.prep_copilot", "PrepCopilotVariant"),
    "PrepVariantName": ("xfinaudio.recommendation.prep_copilot", "PrepVariantName"),
    "DEFAULT_SCORING_CONFIG": ("xfinaudio.recommendation.scoring", "DEFAULT_SCORING_CONFIG"),
    "PlaylistStrategy": ("xfinaudio.recommendation.strategies", "PlaylistStrategy"),
    "ScoringWeights": ("xfinaudio.recommendation.scoring", "ScoringWeights"),
    "SequenceRecommendation": ("xfinaudio.recommendation.optimizer", "SequenceRecommendation"),
    "StrategyRegistry": ("xfinaudio.recommendation.strategies", "StrategyRegistry"),
    "ThresholdScore": ("xfinaudio.recommendation.scoring", "ThresholdScore"),
    "TransitionScore": ("xfinaudio.recommendation.scoring", "TransitionScore"),
    "TransitionScoringConfig": ("xfinaudio.recommendation.scoring", "TransitionScoringConfig"),
    "apply_controls": ("xfinaudio.recommendation.controls", "apply_controls"),
    "build_prep_copilot_plan": ("xfinaudio.recommendation.prep_copilot", "build_prep_copilot_plan"),
    "available_strategies": ("xfinaudio.recommendation.strategies", "available_strategies"),
    "default_strategy_registry": ("xfinaudio.recommendation.strategies", "default_strategy_registry"),
    "get_strategy": ("xfinaudio.recommendation.strategies", "get_strategy"),
    "parse_camelot_key": ("xfinaudio.recommendation.camelot", "parse_camelot_key"),
    "recommend_playlist": ("xfinaudio.recommendation.playlist_service", "recommend_playlist"),
    "recommend_sequence": ("xfinaudio.recommendation.optimizer", "recommend_sequence"),
    "score_camelot_transition": ("xfinaudio.recommendation.camelot", "score_camelot_transition"),
    "score_transition": ("xfinaudio.recommendation.scoring", "score_transition"),
}

__all__ = [
    "AppliedControls",
    "CamelotKey",
    "DJControls",
    "DJSetIntent",
    "PlaylistRecommendation",
    "PrepCopilotPlan",
    "PrepCopilotVariant",
    "PrepVariantName",
    "DEFAULT_SCORING_CONFIG",
    "PlaylistStrategy",
    "ScoringWeights",
    "SequenceRecommendation",
    "StrategyRegistry",
    "ThresholdScore",
    "TransitionScore",
    "TransitionScoringConfig",
    "apply_controls",
    "build_prep_copilot_plan",
    "available_strategies",
    "default_strategy_registry",
    "get_strategy",
    "parse_camelot_key",
    "recommend_playlist",
    "recommend_sequence",
    "score_camelot_transition",
    "score_transition",
]


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily to avoid package-level dependency cycles."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
