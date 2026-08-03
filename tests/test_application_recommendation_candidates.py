from __future__ import annotations

from pathlib import Path

import pytest

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist


def _record(path: str, *, genre: str | None = None, tags: list[str] | None = None) -> TrackRecord:
    return TrackRecord(path=path, metadata_status="complete", genre=genre, tags=tags or [])


def _spectral_record(path: str, color: ColorName) -> TrackRecord:
    return _record(path).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=1.0 if color == "RED" else 0.0,
                green_ratio=1.0 if color == "GREEN" else 0.0,
                blue_ratio=1.0 if color == "BLUE" else 0.0,
                dominant_color=color,
            )
        }
    )


def test_application_candidate_pool_preserves_control_priority() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    priority = _record("/priority.mp3")
    other = _record("/other.mp3")

    result = plan_recommendation_candidates(
        scanned_records=[other, priority],
        controls=DJControls(start_path="/priority.mp3"),
        limit=25,
    )

    assert [track.path for track in result] == ["/priority.mp3", "/other.mp3"]


def test_application_candidate_pool_preserves_compatible_ordering() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    anchor = _record("/anchor.mp3", genre="techno")
    compatible = _record("/compatible.mp3", genre="techno")
    unrelated = _record("/unrelated.mp3", genre="jazz")

    result = plan_recommendation_candidates(
        scanned_records=[anchor, unrelated, compatible],
        controls=DJControls(start_path="/anchor.mp3"),
        limit=25,
    )

    paths = [track.path for track in result]
    assert paths.index("/compatible.mp3") < paths.index("/unrelated.mp3")


def test_application_candidate_pool_prefilters_by_strategy_before_the_interactive_cap() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    reds = [_spectral_record(f"/a-red-{index:02d}.mp3", "RED") for index in range(30)]
    greens = [_spectral_record(f"/b-green-{index:02d}.mp3", "GREEN") for index in range(30)]

    result = plan_recommendation_candidates(
        scanned_records=[*reds, *greens],
        controls=DJControls(start_path="/b-green-00.mp3"),
        limit=25,
        strategy_name="same_color",
    )

    assert len(result) == 25
    assert all(track.spectral_profile is not None for track in result)
    assert {track.spectral_profile.dominant_color for track in result} == {"GREEN"}


def test_application_candidate_pool_keeps_legacy_behavior_without_a_strategy() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    reds = [_spectral_record(f"/a-red-{index:02d}.mp3", "RED") for index in range(30)]
    greens = [_spectral_record(f"/b-green-{index:02d}.mp3", "GREEN") for index in range(30)]

    result = plan_recommendation_candidates(
        scanned_records=[*reds, *greens],
        controls=None,
        limit=25,
    )

    assert [track.path for track in result] == [red.path for red in reds[:25]]


def test_desktop_main_window_imports_application_candidate_boundary() -> None:
    source = Path("src/xfinaudio/desktop/main_window.py").read_text()

    # main_window imports the candidate pool through the application boundary,
    # never directly from the recommendation candidate_pool module. The import
    # may be single- or multi-line (ruff/isort groups same-module symbols), so
    # assert on the boundary module + symbol rather than an exact one-line form.
    assert "from xfinaudio.application.recommendation_candidates import" in source
    assert "plan_recommendation_candidates" in source
    assert "from xfinaudio.recommendation.candidate_pool import build_recommendation_pool" not in source


# ---------------------------------------------------------------------------
# B10/B11 — dedupe runs before the 25-cap, for both the strategy and
# no-strategy branches.
# ---------------------------------------------------------------------------


def _duplicate_pool_records() -> list[TrackRecord]:
    """30 records: a duplicate pair sorted first by path, followed by 28 distinct.

    Paths are prefixed (`/00-...`) so the duplicate pair sorts first
    regardless of whether the caller re-sorts by path (strategy branch) or
    keeps scan order (no-strategy branch) — isolating the dedupe-before-cap
    assertion from unrelated path-sort behavior. If dedupe did not run before
    the cap, the 25-slot pool would contain both duplicate-group members and
    only 24 distinct singles; with dedupe running first, the pool contains one
    representative of the duplicate pair plus 24 other distinct tracks,
    filling all 25 slots with no duplicate-group collapse.
    """
    duplicate_pair = [
        _record("/00-dup-a.mp3"),
        _record("/00-dup-b.mp3"),
    ]
    duplicate_pair[0] = duplicate_pair[0].model_copy(update={"title": "Too Hot", "artist": "Glenn Jones"})
    duplicate_pair[1] = duplicate_pair[1].model_copy(
        update={"title": "Too Hot - 8A - Energy 7", "artist": "Glenn Jones"}
    )
    distinct = [
        _record(f"/10-distinct-{index:02d}.mp3").model_copy(
            update={"title": f"Distinct Song {index:02d}", "artist": "Other Artist"}
        )
        for index in range(28)
    ]
    return [*duplicate_pair, *distinct]


def test_plan_recommendation_candidates_dedupes_before_cap_without_strategy() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    result = plan_recommendation_candidates(
        scanned_records=_duplicate_pool_records(),
        controls=None,
        limit=25,
    )

    assert len(result) == 25
    duplicate_paths_present = {track.path for track in result} & {"/00-dup-a.mp3", "/00-dup-b.mp3"}
    assert len(duplicate_paths_present) == 1


# ---------------------------------------------------------------------------
# CRITICAL 1 correction (native 4R review): an incomplete control track must
# never win a duplicate group over a complete non-control sibling, since
# `build_recommendation_pool` drops incomplete records (including incomplete
# controls) entirely — suppressing the complete sibling in favor of the
# incomplete control caused total silent song loss.
# ---------------------------------------------------------------------------


def test_plan_recommendation_candidates_does_not_lose_complete_track_to_incomplete_locked_duplicate() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    complete = TrackRecord(path="/complete.mp3", title="Song", artist="Artist", metadata_status="complete")
    locked_incomplete = TrackRecord(
        path="/locked.mp3",
        title="Song (v2)",
        artist="Artist",
        metadata_status="incomplete",
        missing_required_fields=["bpm"],
    )

    result = plan_recommendation_candidates(
        scanned_records=[complete, locked_incomplete],
        controls=DJControls(locked_paths={"/locked.mp3"}),
        limit=25,
    )

    assert [track.path for track in result] == ["/complete.mp3"]


def test_plan_recommendation_candidates_dedupes_before_cap_with_strategy() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    # `same_vibe` has no energy/bpm hard range and a stable path sort_hint, so
    # this isolates the dedupe-before-cap behavior from unrelated
    # strategy-specific reordering/filtering.
    result = plan_recommendation_candidates(
        scanned_records=_duplicate_pool_records(),
        controls=None,
        limit=25,
        strategy_name="same_vibe",
    )

    assert len(result) == 25
    duplicate_paths_present = {track.path for track in result} & {"/00-dup-a.mp3", "/00-dup-b.mp3"}
    assert len(duplicate_paths_present) == 1


def test_pool_scales_with_the_requested_slot() -> None:
    """A longer slot needs more candidates, or the set runs out of music.

    With a fixed pool of 50 the track count bottomed out at 11 regardless of
    slot length, because compatible candidates ran out before the slot filled.
    Measured on the real library at a 30-minute slot: score 0.8811 at a pool of
    50, 0.9057 at 120.
    """
    from xfinaudio.application.recommendation_candidates import pool_size_for_slot

    assert pool_size_for_slot(slot_minutes=30.0, played_seconds_per_track=120.0) > pool_size_for_slot(
        slot_minutes=15.0, played_seconds_per_track=120.0
    )
    assert pool_size_for_slot(slot_minutes=60.0, played_seconds_per_track=120.0) > pool_size_for_slot(
        slot_minutes=30.0, played_seconds_per_track=120.0
    )


def test_pool_covers_the_expected_track_count_several_times_over() -> None:
    """The optimizer needs options, not just enough tracks to fill the slot."""
    from xfinaudio.application.recommendation_candidates import pool_size_for_slot

    expected_tracks = 30 * 60 / 120  # a 30-minute slot at two minutes each

    pool = pool_size_for_slot(slot_minutes=30.0, played_seconds_per_track=120.0)

    assert pool >= expected_tracks * 4


def test_pool_is_capped_so_long_slots_stay_responsive() -> None:
    """Quality keeps creeping up with pool size, but cost climbs faster.

    Measured: a pool of 160 scored 0.9083 against 0.9057 at 120 -- a third of a
    percent -- for 2.33s per set against 0.93s.
    """
    from xfinaudio.application.recommendation_candidates import pool_size_for_slot

    assert pool_size_for_slot(slot_minutes=240.0, played_seconds_per_track=120.0) <= 150


def test_shorter_segments_need_a_bigger_pool() -> None:
    """Playing less of each track means more tracks in the same slot."""
    from xfinaudio.application.recommendation_candidates import pool_size_for_slot

    assert pool_size_for_slot(slot_minutes=30.0, played_seconds_per_track=60.0) > pool_size_for_slot(
        slot_minutes=30.0, played_seconds_per_track=180.0
    )


# ---------------------------------------------------------------------------
# Phase 5 (slice 3) — public list API compatibility + internal context seam
# for same_color_energy anchor transport.
# ---------------------------------------------------------------------------


def _energy_spectral_record(path: str, color: ColorName, energy_level: int) -> TrackRecord:
    return _spectral_record(path, color).model_copy(update={"energy_level": energy_level})


def test_plan_recommendation_candidates_returns_list_for_combined_strategy() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    greens = [_energy_spectral_record(f"/g-{index:02d}.mp3", "GREEN", 7) for index in range(5)]

    result = plan_recommendation_candidates(
        scanned_records=greens,
        controls=DJControls(start_path="/g-00.mp3"),
        limit=25,
        strategy_name="same_color_energy",
    )

    assert isinstance(result, list)
    assert all(isinstance(track, TrackRecord) for track in result)
    # Strict eligibility keeps only the GREEN, energy-7 candidates (anchor is GREEN/7).
    assert all(track.spectral_profile is not None for track in result)
    assert {track.spectral_profile.dominant_color for track in result} == {"GREEN"}


def test_plan_recommendation_candidates_returns_list_for_ordinary_strategy() -> None:
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates

    greens = [_spectral_record(f"/g-{index:02d}.mp3", "GREEN") for index in range(5)]

    result = plan_recommendation_candidates(
        scanned_records=greens,
        controls=DJControls(start_path="/g-00.mp3"),
        limit=25,
        strategy_name="same_color",
    )

    assert isinstance(result, list)
    assert all(isinstance(track, TrackRecord) for track in result)


def test_context_planner_returns_frozen_context_with_bound_anchor_path() -> None:
    from xfinaudio.application.recommendation_candidates import (
        RecommendationCandidateContext,
        _plan_same_color_energy_candidate_context,
    )

    greens = [_energy_spectral_record(f"/g-{index:02d}.mp3", "GREEN", 7) for index in range(5)]

    context = _plan_same_color_energy_candidate_context(
        scanned_records=greens,
        controls=DJControls(start_path="/g-00.mp3"),
        limit=25,
    )

    assert isinstance(context, RecommendationCandidateContext)
    assert context.same_color_energy_anchor_path == "/g-00.mp3"
    assert isinstance(context.records, list)
    assert "/g-00.mp3" in {track.path for track in context.records}
    # Frozen dataclass: attributes cannot be reassigned.
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        context.records = []  # type: ignore[misc]


def test_context_anchor_survives_dedupe_and_cap() -> None:
    """A no-control first-profile anchor with a dedupe-colliding sibling.

    The bound anchor path must survive `dedupe_recommendation_duplicates` (which
    would otherwise pick the OTHER sibling as representative) and the interactive
    cap, reaching the returned context. Anchor is never re-resolved after
    dedupe/cap and never converted to `start_path`.
    """
    from xfinaudio.application.recommendation_candidates import _plan_same_color_energy_candidate_context

    # Two dedupe-group siblings; the anchor is the first profiled record but the
    # representative sort key (shorter title) would otherwise prefer the sibling.
    anchor = _energy_spectral_record("/00-anchor.mp3", "GREEN", 7).model_copy(
        update={"title": "Song (Extended Mix)", "artist": "Artist"}
    )
    dedupe_sibling = _energy_spectral_record("/00-sibling.mp3", "GREEN", 7).model_copy(
        update={"title": "Song", "artist": "Artist"}
    )
    fillers = [_energy_spectral_record(f"/g-{index:02d}.mp3", "GREEN", 7) for index in range(5)]

    context = _plan_same_color_energy_candidate_context(
        scanned_records=[anchor, dedupe_sibling, *fillers],
        controls=None,
        limit=25,
    )

    assert context.same_color_energy_anchor_path == "/00-anchor.mp3"
    assert "/00-anchor.mp3" in {track.path for track in context.records}


def test_final_enforcement_uses_bound_anchor_path_when_supplied() -> None:
    """`recommend_playlist(..., same_color_energy_anchor_path=...)` binds THAT track.

    When the caller supplies a bound path, final enforcement resolves eligibility
    against that specific anchor rather than re-resolving from the (possibly
    deduped/capped) pool.
    """
    anchor = _energy_spectral_record("/anchor.mp3", "GREEN", 7)
    matching = _energy_spectral_record("/match.mp3", "GREEN", 7)
    wrong_energy = _energy_spectral_record("/wrong.mp3", "GREEN", 3)

    recommendation = recommend_playlist(
        [anchor, matching, wrong_energy],
        "same_color_energy",
        controls=DJControls(),
        same_color_energy_anchor_path="/anchor.mp3",
    )

    result_paths = {track.path for track in recommendation.ordered_tracks}
    assert "/wrong.mp3" not in result_paths
    assert "/match.mp3" in result_paths


def test_supplied_missing_anchor_path_fails_closed() -> None:
    """A supplied path absent from the pool fails closed — never re-resolved."""
    green = _energy_spectral_record("/g.mp3", "GREEN", 7)

    recommendation = recommend_playlist(
        [green],
        "same_color_energy",
        controls=DJControls(),
        same_color_energy_anchor_path="/does-not-exist.mp3",
    )

    # Anchor could not be bound -> prerequisite fails closed -> no generated candidates.
    assert recommendation.ordered_tracks == []
    assert any("prerequisite" in warning for warning in recommendation.warnings)
