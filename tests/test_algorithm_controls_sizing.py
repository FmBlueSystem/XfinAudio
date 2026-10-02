"""Independent public-contract regressions from the algorithm audit."""

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan


def record(path: str, duration: float | None = 240, bpm: float = 120) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        bpm=bpm,
        camelot_key="8A",
        energy_level=5,
        duration=duration,
        genre="House",
        metadata_status="complete",
    )


@pytest.mark.parametrize("control", ["end", "locked"])
def test_capped_non_arc_preserves_requested_control(control: str) -> None:
    controls = DJControls(
        start_path="a", end_path="d" if control == "end" else None, locked_paths={"d"} if control == "locked" else set()
    )
    result = recommend_playlist([record(p) for p in "abcd"], "same_energy", controls, target_count=2)
    assert [t.path for t in result.ordered_tracks] == ["a", "d"]


def test_count_conflict_does_not_silently_discard_manual_tracks() -> None:
    result = recommend_playlist(
        [record(p) for p in "abcd"], "harmonic_journey", DJControls(manual_order_paths=["a", "b", "c"]), target_count=2
    )
    assert result.ordered_tracks == []
    assert any("mandatory" in warning.lower() and "count" in warning.lower() for warning in result.warnings)


def test_prep_count_is_known_before_terminal_selection() -> None:
    plan = build_prep_copilot_plan(
        [record(p) for p in "abcdef"], DJSetIntent(name="test", start_path="a", end_path="f", target_track_count=3)
    )
    for variant in plan.variants:
        paths = [t.path for t in variant.recommendation.ordered_tracks]
        assert len(paths) == 3
        assert paths[0] == "a" and paths[-1] == "f"


def test_duration_arc_covers_nonintegral_slot() -> None:
    result = recommend_playlist([record(p) for p in "abcdef"], "harmonic_journey", target_duration_minutes=9)
    assert len(result.ordered_tracks) == 3
    assert sum(t.duration or 0 for t in result.ordered_tracks) >= 540


def test_duration_arc_checks_actual_selection_not_pool_mean() -> None:
    pool = [record(p, 60 if p < "e" else 600) for p in "abcdef"]
    result = recommend_playlist(pool, "harmonic_journey", target_duration_minutes=9)
    assert sum(t.duration or 0 for t in result.ordered_tracks) >= 540


@pytest.mark.parametrize("duration", [60, None])
def test_duration_shortage_is_explicit(duration: float | None) -> None:
    result = recommend_playlist([record(p, duration) for p in "abc"], "harmonic_journey", target_duration_minutes=9)
    assert any(
        "duration" in warning.lower() and ("short" in warning.lower() or "unknown" in warning.lower())
        for warning in result.warnings
    )


@pytest.mark.parametrize("requested,excluded", [(40, 0), (10, 20)])
def test_prep_eligible_pool_can_fill_requested_count(requested: int, excluded: int) -> None:
    pool = [record(f"{i:03}") for i in range(60)]
    plan = build_prep_copilot_plan(
        pool, DJSetIntent(name="pool", target_track_count=requested, excluded_paths={t.path for t in pool[:excluded]})
    )
    for variant in plan.variants:
        assert len(variant.recommendation.ordered_tracks) == requested
        assert not ({t.path for t in variant.recommendation.ordered_tracks} & {t.path for t in pool[:excluded]})


def test_count_shortage_is_visible_even_above_near_empty_threshold() -> None:
    result = recommend_playlist([record(p) for p in "abc"], "harmonic_journey", target_count=8)
    assert any("count" in warning.lower() and "short" in warning.lower() for warning in result.warnings)
