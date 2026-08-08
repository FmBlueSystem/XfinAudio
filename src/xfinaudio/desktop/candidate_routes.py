"""Shared candidate-route resolution for the desktop recommendation entry points."""

from __future__ import annotations

from collections.abc import Callable

from xfinaudio.application.recommendation_candidates import RecommendationCandidateContext
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import COLOR_FILTER_STRATEGIES

RecommendationRecordsRoute = Callable[..., list[TrackRecord]]
ColorAnchorContextRoute = Callable[..., RecommendationCandidateContext]


def resolve_candidate_route(
    controls: DJControls | None,
    strategy_name: str | None,
    *,
    records_route: RecommendationRecordsRoute,
    color_anchor_context_route: ColorAnchorContextRoute,
) -> tuple[list[TrackRecord], str | None]:
    """Return the candidate pool for this strategy plus the colour anchor bound to it.

    The colour strategies transport a bound anchor path so every downstream consumer
    gates against the same track the pool was planned for, instead of re-resolving an
    anchor after dedupe and cap. Every other strategy stays on the plain records route
    and binds no anchor, so `None` is the honest answer for them -- not a missing value.

    Both desktop entry points -- `RecommendationService.recommend` and
    `PrepCopilotController.generate` -- resolve through here, so the branch that decides
    which route a strategy takes exists once and the two cannot drift apart.

    The routes arrive as parameters rather than being imported: both callers end up at
    the same `MainWindow` methods, but through different injection seams, and which seam
    is none of this function's business.
    """
    if strategy_name in COLOR_FILTER_STRATEGIES:
        context = color_anchor_context_route(controls, strategy_name)
        return context.records, context.color_anchor_path
    return records_route(controls, strategy_name), None
