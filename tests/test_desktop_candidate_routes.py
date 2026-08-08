"""Contract tests for the shared desktop candidate-route resolver.

Both desktop entry points (`RecommendationService.recommend` and
`PrepCopilotController.generate`) pin this routing through their own suites, but
neither pins the resolver itself. These tests hold the seam directly: which route a
strategy takes, what reaches it, and that the unchosen route is never called.
"""

from typing import Any, cast

import pytest

from xfinaudio.application.recommendation_candidates import RecommendationCandidateContext
from xfinaudio.desktop.candidate_routes import resolve_candidate_route
from xfinaudio.recommendation.playlist_service import COLOR_FILTER_STRATEGIES


def _unrouted(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("this candidate route must not be reached")


@pytest.mark.parametrize("strategy_name", sorted(COLOR_FILTER_STRATEGIES))
def test_colour_strategies_resolve_through_the_context_route(strategy_name: str) -> None:
    """Every colour strategy returns the context's records AND its bound anchor."""
    controls = cast(Any, object())
    context_records: list[Any] = [object()]
    context_calls: list[tuple[Any, Any]] = []

    def context_route(controls_arg: Any, strategy_arg: str) -> RecommendationCandidateContext:
        context_calls.append((controls_arg, strategy_arg))
        return RecommendationCandidateContext(records=context_records, color_anchor_path="/music/anchor.flac")

    records, color_anchor_path = resolve_candidate_route(
        controls,
        strategy_name,
        records_route=_unrouted,
        color_anchor_context_route=context_route,
    )

    assert context_calls == [(controls, strategy_name)]
    assert records is context_records
    assert color_anchor_path == "/music/anchor.flac"


def test_ordinary_strategies_resolve_through_the_records_route_and_bind_no_anchor() -> None:
    """A non-colour strategy takes the plain route; `None` is its honest anchor."""
    controls = cast(Any, object())
    plain_records: list[Any] = [object()]
    records_calls: list[tuple[Any, Any]] = []

    def records_route(controls_arg: Any, strategy_arg: str | None = None) -> list[Any]:
        records_calls.append((controls_arg, strategy_arg))
        return plain_records

    records, color_anchor_path = resolve_candidate_route(
        controls,
        "same_genre",
        records_route=records_route,
        color_anchor_context_route=_unrouted,
    )

    assert records_calls == [(controls, "same_genre")]
    assert records is plain_records
    assert color_anchor_path is None


def test_absent_strategy_resolves_through_the_records_route() -> None:
    """`currentData()` yields `None` for an unpopulated combo; that is not a colour strategy.

    The membership test must treat a missing strategy as ordinary rather than raising
    or reaching the colour route, which would demand an anchor nothing has bound yet.
    """
    records, color_anchor_path = resolve_candidate_route(
        None,
        None,
        records_route=lambda _controls, _strategy=None: [],
        color_anchor_context_route=_unrouted,
    )

    assert records == []
    assert color_anchor_path is None


def test_a_colour_context_that_binds_no_anchor_still_returns_its_records() -> None:
    """`color_anchor_path=None` from the context seam is a fallback, not a failure.

    The colour route can legitimately fail to bind an anchor. That must pass through as
    `None` so `recommend_playlist` resolves one itself, rather than being turned into a
    fail-closed empty pool here.
    """
    context_records: list[Any] = [object()]

    records, color_anchor_path = resolve_candidate_route(
        cast(Any, object()),
        "same_color",
        records_route=_unrouted,
        color_anchor_context_route=lambda _controls, _strategy: RecommendationCandidateContext(
            records=context_records, color_anchor_path=None
        ),
    )

    assert records is context_records
    assert color_anchor_path is None
