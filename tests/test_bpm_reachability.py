"""Folded BPM reachability against an independent all-pairs graph traversal."""

import math
import random
from unittest.mock import patch

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import _bpm_reachable_from, recommend_playlist
from xfinaudio.recommendation.scoring import bpm_difference_percent


def track(path: str, bpm: float | None) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        bpm=bpm,
        camelot_key="8A",
        energy_level=5,
        duration=240.0,
        metadata_status="complete",
    )


def exhaustive_reachable(pool: list[TrackRecord], anchor: str | None, protected: set[str], ceiling: float) -> list[str]:
    """Reference BFS enumerates every edge; no production window/index logic."""
    nodes = sorted(
        (item for item in pool if item.bpm is not None and (item.path == anchor or item.path not in protected)),
        key=lambda item: (item.bpm or 0.0, item.path),
    )
    remaining = {item.path: item for item in nodes}
    components: list[set[str]] = []
    for root in nodes:
        if root.path not in remaining:
            continue
        component = {root.path}
        frontier = [remaining.pop(root.path)]
        while frontier:
            current = frontier.pop()
            adjacent = [
                item
                for item in remaining.values()
                if bpm_difference_percent(current.bpm or 0.0, item.bpm or 0.0) <= ceiling
            ]
            for item in adjacent:
                component.add(item.path)
                frontier.append(remaining.pop(item.path))
        components.append(component)
    chosen = next((part for part in components if anchor in part), None)
    if chosen is None:
        chosen = max(components, key=len, default=set())
    return [
        item.path
        for item in pool
        if item.bpm is None or item.path == anchor or item.path in protected or item.path in chosen
    ]


def test_folded_reachability_ignores_intervening_unconnected_tempo() -> None:
    pool = [track("a60", 60), track("b90", 90), track("c120", 120)]
    result = recommend_playlist(pool, "harmonic_journey", controls=DJControls(start_path="a60"), target_count=2)
    assert [item.path for item in result.ordered_tracks] == ["a60", "c120"]
    assert any("Dropped 1 generated track(s)" in warning for warning in result.warnings)
    assert not any("Dropped 2 generated track(s)" in warning for warning in result.warnings)


@pytest.mark.parametrize("ceiling", [0.0, 0.1, 1.0, 2.0, 3.0, 10.0, 100.0])
@pytest.mark.parametrize("seed", range(12))
def test_reachability_matches_exhaustive_folded_components(ceiling: float, seed: int) -> None:
    rng = random.Random(seed)
    bpms = [None, 0.0, 60.0, 61.0, 90.0, 117.6, 120.0, 122.4, 180.0, 240.0]
    for _ in range(12):
        pool = [track(f"track-{i}", rng.choice(bpms)) for i in range(rng.randint(1, 15))]
        rng.shuffle(pool)
        anchor = rng.choice([None, "missing", *[item.path for item in pool]])
        protected = {item.path for item in pool if rng.random() < 0.2}
        expected = exhaustive_reachable(pool, anchor, protected, ceiling)
        kept, dropped = _bpm_reachable_from(pool, anchor, preserve_paths=protected, max_bpm_difference_percent=ceiling)
        assert [item.path for item in kept] == expected
        assert dropped == len(pool) - len(expected)


@pytest.mark.parametrize("ceiling", [0.0, 0.1, 1.0, 2.0, 3.0])
def test_reachability_matches_comparator_at_window_boundaries(ceiling: float) -> None:
    for boundary in [60 * (1 + ceiling / 100), 60 * 1.96, 60 * 2.04, 120 / (1 + ceiling / 100)]:
        for bpm in [math.nextafter(boundary, -math.inf), boundary, math.nextafter(boundary, math.inf)]:
            pool = [track("anchor", 60), track("decoy", 90), track("edge", bpm)]
            for anchor in ["anchor", "edge"]:
                expected = exhaustive_reachable(pool, anchor, set(), ceiling)
                kept, _ = _bpm_reachable_from(pool, anchor, max_bpm_difference_percent=ceiling)
                assert [item.path for item in kept] == expected


def test_reachability_preserves_controls_without_using_them_as_bridges() -> None:
    pool = [track("anchor", 60), track("control", 120), track("unreachable", 240), track("unknown", None)]
    kept, dropped = _bpm_reachable_from(pool, "anchor", preserve_paths={"control"})
    assert [item.path for item in kept] == ["anchor", "control", "unknown"]
    assert dropped == 1


def test_dense_folded_reachability_avoids_all_pairs_comparisons() -> None:
    pool = [track(f"slow-{i}", 60 + i / 10000) for i in range(1000)]
    pool += [track("decoy", 90)]
    pool += [track(f"fast-{i}", 120 + i / 10000) for i in range(1000)]
    with patch(
        "xfinaudio.recommendation.playlist_service.bpm_difference_percent", wraps=bpm_difference_percent
    ) as compare:
        kept, dropped = _bpm_reachable_from(pool, "slow-0")
    assert len(kept) == 2000
    assert dropped == 1
    assert compare.call_count < 8 * len(pool)
