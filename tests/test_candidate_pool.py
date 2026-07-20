"""Tests for dedupe_recommendation_duplicates — candidate-pool duplicate-version dedupe.

Spec: specs/recommendation-duplicate-version-dedupe/spec.md
Design: design.md Decision 3b.
"""

from __future__ import annotations

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import dedupe_recommendation_duplicates
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist


def _record(
    path: str,
    title: str = "Song",
    artist: str = "Artist",
    status: str = "complete",
    missing: list[str] | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=artist,
        metadata_status=status,  # type: ignore[arg-type]
        missing_required_fields=missing or [],
    )


# ---------------------------------------------------------------------------
# B6 — a duplicate group collapses to one representative
# ---------------------------------------------------------------------------


def test_dedupe_collapses_too_hot_duplicate_group_to_one_representative():
    # Reproduces the live-observed regression: "Too Hot" appearing twice in the
    # same pool, differing only by an app-generated Camelot/Energy suffix — the
    # same grouping semantics as the existing library duplicate filter (see
    # design.md's regression scenario and spec's "Live-observed regression is
    # fixed" scenario).
    complete = _record("/too-hot-clean.mp3", title="Too Hot", artist="Glenn Jones", status="complete")
    incomplete_suffix = _record(
        "/too-hot-suffixed.mp3",
        title="Too Hot - 8A - Energy 7",
        artist="Glenn Jones",
        status="complete",
    )
    result = dedupe_recommendation_duplicates([complete, incomplete_suffix], controls=None)
    assert len(result) == 1
    assert result[0].path == "/too-hot-clean.mp3"


def test_dedupe_representative_choice_matches_documented_sort_key():
    # Both normalize to the same group key ("song"); same status/missing-count
    # tier, so the shorter *original* title wins the tiebreak.
    short_title = _record("/b.mp3", title="Song", artist="Artist")
    long_title = _record("/a.mp3", title="Song - 8A - Energy 7", artist="Artist")
    result = dedupe_recommendation_duplicates([long_title, short_title], controls=None)
    assert [r.path for r in result] == ["/b.mp3"]


# ---------------------------------------------------------------------------
# B7 — control-path immunity
# ---------------------------------------------------------------------------


def test_dedupe_keeps_locked_duplicate_and_removes_non_control_sibling():
    locked = _record("/locked.mp3", title="Song", artist="Artist", status="complete")
    non_control = _record("/other.mp3", title="Song (v2)", artist="Artist", status="complete")
    controls = DJControls(locked_paths={"/locked.mp3"})
    result = dedupe_recommendation_duplicates([non_control, locked], controls=controls)
    assert [r.path for r in result] == ["/locked.mp3"]


def test_dedupe_keeps_start_track_in_duplicate_group():
    start = _record("/start.mp3", title="Song", artist="Artist", status="complete")
    other = _record("/other.mp3", title="Song (v2)", artist="Artist", status="complete")
    controls = DJControls(start_path="/start.mp3")
    result = dedupe_recommendation_duplicates([other, start], controls=controls)
    assert [r.path for r in result] == ["/start.mp3"]


def test_dedupe_keeps_end_track_in_duplicate_group():
    end = _record("/end.mp3", title="Song", artist="Artist", status="complete")
    other = _record("/other.mp3", title="Song (v2)", artist="Artist", status="complete")
    controls = DJControls(end_path="/end.mp3")
    result = dedupe_recommendation_duplicates([other, end], controls=controls)
    assert [r.path for r in result] == ["/end.mp3"]


def test_dedupe_keeps_manual_order_track_in_duplicate_group_regardless_of_position():
    manual = _record("/manual.mp3", title="Song", artist="Artist", status="complete")
    other = _record("/other.mp3", title="Song (v2)", artist="Artist", status="complete")
    controls = DJControls(manual_order_paths=["/manual.mp3"])
    # Manual control appears last in input order — must still survive.
    result = dedupe_recommendation_duplicates([other, manual], controls=controls)
    assert [r.path for r in result] == ["/manual.mp3"]


def test_dedupe_keeps_all_controls_when_multiple_controls_share_a_group():
    locked = _record("/locked.mp3", title="Song", artist="Artist", status="complete")
    start = _record("/start.mp3", title="Song (v2)", artist="Artist", status="complete")
    controls = DJControls(locked_paths={"/locked.mp3"}, start_path="/start.mp3")
    result = dedupe_recommendation_duplicates([locked, start], controls=controls)
    assert {r.path for r in result} == {"/locked.mp3", "/start.mp3"}


# ---------------------------------------------------------------------------
# B8 — determinism and no-duplicates characterization
# ---------------------------------------------------------------------------


def test_dedupe_is_deterministic_across_repeated_runs():
    complete = _record("/a.mp3", title="Song", artist="Artist", status="complete")
    other_complete = _record("/b.mp3", title="Song (v2)", artist="Artist", status="complete")
    first_run = dedupe_recommendation_duplicates([other_complete, complete], controls=None)
    second_run = dedupe_recommendation_duplicates([other_complete, complete], controls=None)
    assert [r.path for r in first_run] == [r.path for r in second_run] == ["/a.mp3"]


def test_dedupe_no_duplicates_is_byte_identical_and_order_preserving():
    records = [
        _record("/a.mp3", title="Song A", artist="Artist"),
        _record("/b.mp3", title="Song B", artist="Artist"),
        _record("/c.mp3", title="Song C", artist="Artist"),
    ]
    result = dedupe_recommendation_duplicates(records, controls=None)
    assert result == records


def test_dedupe_blank_metadata_tracks_never_collapse():
    first = _record("/a.mp3", title=None, artist="Artist")  # type: ignore[arg-type]
    second = _record("/b.mp3", title=None, artist="Artist")  # type: ignore[arg-type]
    result = dedupe_recommendation_duplicates([first, second], controls=None)
    assert {r.path for r in result} == {"/a.mp3", "/b.mp3"}


def test_dedupe_preserves_original_pool_order_after_suppression():
    keep_first = _record("/keep.mp3", title="Song X", artist="Artist", status="complete")
    duplicate_a = _record("/dup-a.mp3", title="Song", artist="Artist", status="complete")
    duplicate_b = _record("/dup-b.mp3", title="Song (v2)", artist="Artist", status="complete")
    result = dedupe_recommendation_duplicates([duplicate_b, keep_first, duplicate_a], controls=None)
    assert [r.path for r in result] == ["/keep.mp3", "/dup-a.mp3"]


def _spectral_record(
    path: str,
    color: ColorName,
    *,
    title: str = "Song",
    artist: str = "Artist",
    energy_level: int = 5,
    status: str = "complete",
    missing: list[str] | None = None,
) -> TrackRecord:
    return _record(path, title=title, artist=artist, status=status, missing=missing).model_copy(
        update={
            "energy_level": energy_level,
            "spectral_profile": SpectralProfile(
                red_ratio=1.0 if color == "RED" else 0.0,
                green_ratio=1.0 if color == "GREEN" else 0.0,
                blue_ratio=1.0 if color == "BLUE" else 0.0,
                dominant_color=color,
            ),
        }
    )


# ---------------------------------------------------------------------------
# B12 — anchor/energy filters still apply to surviving representatives
# (no bypass introduced by dedupe)
# ---------------------------------------------------------------------------


def test_dedupe_survivor_is_still_filtered_by_anchor_color_under_same_color_energy():
    anchor = _spectral_record("/anchor.mp3", "RED", title="Anchor Song", artist="Anchor Artist")
    # A non-duplicate RED candidate so the color filter has a real match set —
    # otherwise same_color_energy's empty-pool fallback would keep everything,
    # masking whether the dedupe survivor was actually filtered.
    red_candidate = _spectral_record("/red-candidate.mp3", "RED", title="Red Song", artist="Red Artist")
    # Duplicate group: both GREEN (non-matching anchor color), non-control.
    # Dedupe keeps the complete one; that survivor must still be removed by
    # same_color_energy's hard color filter — surviving dedupe grants no
    # exemption from strategy filtering.
    dup_complete = _spectral_record("/dup-complete.mp3", "GREEN", title="Dup Song", artist="Dup Artist")
    dup_suffixed = _spectral_record(
        "/dup-suffixed.mp3",
        "GREEN",
        title="Dup Song - 8A - Energy 7",
        artist="Dup Artist",
        status="complete",
    )
    controls = DJControls(start_path="/anchor.mp3")

    deduped_pool = dedupe_recommendation_duplicates(
        [anchor, red_candidate, dup_complete, dup_suffixed], controls=controls
    )
    # Sanity: dedupe collapsed the GREEN duplicate group to its complete member.
    assert {r.path for r in deduped_pool} == {"/anchor.mp3", "/red-candidate.mp3", "/dup-complete.mp3"}

    result = recommend_playlist(deduped_pool, "same_color_energy", controls=controls)

    paths = {item.path for item in result.ordered_tracks}
    assert paths == {"/anchor.mp3", "/red-candidate.mp3"}
    assert "/dup-complete.mp3" not in paths


# ---------------------------------------------------------------------------
# B14 — duplicate-free libraries are unchanged end-to-end
# (same_color / same_energy / same_color_energy)
# ---------------------------------------------------------------------------


def test_dedupe_free_pool_produces_identical_recommendation_across_strategies():
    anchor = _spectral_record("/anchor.mp3", "RED", title="Anchor Song", artist="Anchor Artist", energy_level=5)
    same_color = _spectral_record("/same-color.mp3", "RED", title="Same Color Song", artist="Other Artist")
    same_energy = _spectral_record(
        "/same-energy.mp3", "GREEN", title="Same Energy Song", artist="Other Artist", energy_level=5
    )
    unrelated = _spectral_record("/unrelated.mp3", "BLUE", title="Unrelated Song", artist="Other Artist")
    pool = [anchor, same_color, same_energy, unrelated]
    controls = DJControls(start_path="/anchor.mp3")

    for strategy_name in ("same_color", "same_energy", "same_color_energy"):
        before = recommend_playlist(pool, strategy_name, controls=controls)
        deduped_pool = dedupe_recommendation_duplicates(pool, controls=controls)
        # No duplicate groups exist (every title+artist key is unique) — dedupe
        # must be a byte-identical no-op, order-preserving.
        assert deduped_pool == pool
        after = recommend_playlist(deduped_pool, strategy_name, controls=controls)
        assert after.ordered_tracks == before.ordered_tracks
        assert after.transition_scores == before.transition_scores
        assert after.warnings == before.warnings


# ---------------------------------------------------------------------------
# Maintainer decision 2026-07-20: candidate-pool dedupe uses the STRICTER
# playlist-level key (parenthetical descriptor content ignored entirely).
# RED fixtures use the three live-observed pairs verbatim.
# ---------------------------------------------------------------------------


def test_dedupe_collapses_too_hot_single_version_and_clean_verbatim_live_pair():
    single_version = _record(
        "/too-hot-single.mp3", title="Too Hot (Single Version)", artist="Glenn Jones", status="complete"
    )
    clean = _record("/too-hot-clean.mp3", title="Too Hot (Clean)", artist="Glenn Jones", status="complete")
    result = dedupe_recommendation_duplicates([single_version, clean], controls=None)
    assert len(result) == 1


def test_dedupe_collapses_se_la_verbatim_live_pair():
    se_la = _record("/se-la.mp3", title="Se La", artist="Teena Marie", status="complete")
    se_la_12 = _record("/se-la-12.mp3", title='Se La (12" Version)', artist="Teena Marie", status="complete")
    result = dedupe_recommendation_duplicates([se_la, se_la_12], controls=None)
    assert len(result) == 1


def test_dedupe_collapses_still_verbatim_live_pair():
    still = _record("/still.mp3", title="Still", artist="The Whispers", status="complete")
    still_suffixed = _record(
        "/still-suffixed.mp3", title="Still - 3B - Energy 3", artist="The Whispers", status="complete"
    )
    result = dedupe_recommendation_duplicates([still, still_suffixed], controls=None)
    assert len(result) == 1


def test_dedupe_all_three_live_pairs_collapse_in_one_pool():
    pool = [
        _record("/too-hot-single.mp3", title="Too Hot (Single Version)", artist="Glenn Jones", status="complete"),
        _record("/too-hot-clean.mp3", title="Too Hot (Clean)", artist="Glenn Jones", status="complete"),
        _record("/se-la.mp3", title="Se La", artist="Teena Marie", status="complete"),
        _record("/se-la-12.mp3", title='Se La (12" Version)', artist="Teena Marie", status="complete"),
        _record("/still.mp3", title="Still", artist="The Whispers", status="complete"),
        _record("/still-suffixed.mp3", title="Still - 3B - Energy 3", artist="The Whispers", status="complete"),
    ]
    result = dedupe_recommendation_duplicates(pool, controls=None)
    assert len(result) == 3


def test_dedupe_distinct_songs_outside_parens_never_collapse():
    # Negative guard: titles sharing a leading word but differing outside any
    # parenthetical must remain distinct even under the stricter playlist key.
    rocks = _record("/rocks.mp3", title="Love On The Rocks", artist="Diana Ross", status="complete")
    tender = _record("/tender.mp3", title="Love Me Tender", artist="Elvis Presley", status="complete")
    result = dedupe_recommendation_duplicates([rocks, tender], controls=None)
    assert {r.path for r in result} == {"/rocks.mp3", "/tender.mp3"}


# ---------------------------------------------------------------------------
# CRITICAL 2 correction (native 4R review): distinct fully-parenthetical
# titles (e.g. "(Intro)"/"(Outro)") must never collapse just because both
# normalize to an empty playlist-grouping title.
# ---------------------------------------------------------------------------


def test_dedupe_does_not_collapse_distinct_fully_parenthetical_titles():
    intro = _record("/intro.mp3", title="(Intro)", artist="Artist", status="complete")
    outro = _record("/outro.mp3", title="(Outro)", artist="Artist", status="complete")
    result = dedupe_recommendation_duplicates([intro, outro], controls=None)
    assert {r.path for r in result} == {"/intro.mp3", "/outro.mp3"}


def test_dedupe_excluded_manual_path_is_not_treated_as_preserved():
    # `manual_order_paths` is not validated against `excluded_paths` overlap by
    # `DJControls` itself, so the dedupe preserve-set must still subtract
    # excluded paths explicitly (matching `_preserved_control_paths` semantics).
    # Titles are swapped vs. a plain "Song"/"Song (v2)" pair so that, once both
    # are complete (per the CRITICAL 1 fix, only complete records are
    # grouped), `other`'s shorter title still wins the sort-key tiebreak —
    # proving `excluded_manual` loses on the merits, not because it was ever
    # a preserved control.
    excluded_manual = _record("/manual.mp3", title="Song (v2)", artist="Artist", status="complete")
    other = _record("/other.mp3", title="Song", artist="Artist", status="complete")
    controls = DJControls(manual_order_paths=["/manual.mp3"], excluded_paths={"/manual.mp3"})
    result = dedupe_recommendation_duplicates([excluded_manual, other], controls=controls)
    assert len(result) == 1
    assert result[0].path == "/other.mp3"
