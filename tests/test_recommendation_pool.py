"""Tests for strategy-aware candidate-pool selection."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.pool import build_recommendation_pool
from xfinaudio.recommendation.strategies import get_strategy


def _record(
    path: str,
    *,
    bpm: float = 120.0,
    energy_level: int = 5,
    tags: list[str] | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        bpm=bpm,
        camelot_key="8A",
        energy_level=energy_level,
        genre="house",
        tags=tags if tags is not None else ["peak"],
        metadata_status="complete",
    )


def test_pool_without_strategy_is_unchanged() -> None:
    records = [_record(f"t{i}", bpm=120.0 + i) for i in range(5)]
    pool = build_recommendation_pool(records, controls=None, limit=25)
    assert {r.path for r in pool} == {r.path for r in records}


def test_pool_strategy_filters_out_of_range_candidates() -> None:
    # chill: energy_range (1, 5), bpm_range (0, 118)
    anchor = _record("anchor", bpm=128.0, energy_level=9, tags=["peak"])
    in_range = [_record(f"in{i}", bpm=110.0, energy_level=3, tags=["peak"]) for i in range(6)]
    out_range = [_record(f"out{i}", bpm=130.0, energy_level=9, tags=["peak"]) for i in range(6)]
    controls = DJControls(manual_order_paths=["anchor"])

    pool = build_recommendation_pool(
        [anchor, *in_range, *out_range],
        controls,
        limit=25,
        strategy=get_strategy("chill"),
    )
    paths = {r.path for r in pool}

    assert "anchor" in paths  # priority/anchor preserved regardless of range
    assert any(p.startswith("in") for p in paths)
    assert not any(p.startswith("out") for p in paths)  # out-of-range excluded upstream


def test_pool_strategy_prevents_collapse_when_out_of_range_dominates() -> None:
    # Many out-of-range tracks share the anchor tag and would dominate a strategy-blind pool,
    # starving the in-range candidates a chill set needs.
    anchor = _record("anchor", bpm=112.0, energy_level=4, tags=["shared"])
    in_range = [_record(f"in{i}", bpm=110.0 + (i % 5), energy_level=3, tags=["shared"]) for i in range(8)]
    out_range = [_record(f"out{i}", bpm=130.0, energy_level=9, tags=["shared"]) for i in range(40)]
    controls = DJControls(manual_order_paths=["anchor"])

    pool = build_recommendation_pool(
        [anchor, *in_range, *out_range],
        controls,
        limit=25,
        strategy=get_strategy("chill"),
    )
    in_range_in_pool = [r for r in pool if r.path.startswith("in")]
    assert len(in_range_in_pool) == 8  # all in-range candidates survive instead of being starved
