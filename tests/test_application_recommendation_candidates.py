from __future__ import annotations

from pathlib import Path

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls


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

    assert "from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates" in source
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
