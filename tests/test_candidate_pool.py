"""Tests for dedupe_recommendation_duplicates — candidate-pool duplicate-version dedupe.

Spec: specs/recommendation-duplicate-version-dedupe/spec.md
Design: design.md Decision 3b.
"""

from __future__ import annotations

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation import candidate_pool
from xfinaudio.recommendation.candidate_pool import (
    _track_similarity_key,
    build_recommendation_pool,
    dedupe_recommendation_duplicates,
    track_triad_identities,
)
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist


def track(path: str, *, energy_level: int | None = 5) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path.rsplit("/", maxsplit=1)[-1],
        bpm=126.0,
        camelot_key="8A",
        energy_level=energy_level,
        duration=240.0,
        genre="House",
        tags=["house"],
        metadata_status="complete",
    )


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
                # Finite positive centroid/rolloff so same-label candidates share
                # the gate's relative-delta denominators (delta 0) and pass the
                # bounded proximity gate, which since tighten-spectral-color-filters
                # spans every dominant-color label, not only MIXED.
                centroid_hz=1000.0,
                rolloff_hz=2000.0,
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


def _energy_levels(tracks) -> set[int]:
    return {track.energy_level for track in tracks if track.energy_level is not None}


def test_energy_spread_reserves_room_for_levels_the_arc_needs() -> None:
    """Similarity ranking fills the pool with the anchor's own energy.

    Measured on a real library: with an E7 anchor, up to 80% of a 120-track pool
    landed on level 7, so the arc had nothing to build a shape from. A set needs
    material at the ends, even at the cost of some transition quality.
    """
    anchor = track("/anchor.flac", energy_level=7)
    crowd = [track(f"/same{index}.flac", energy_level=7) for index in range(200)]
    sparse = [track(f"/low{index}.flac", energy_level=4) for index in range(5)]
    sparse += [track(f"/high{index}.flac", energy_level=9) for index in range(5)]

    pool = build_recommendation_pool(
        [anchor, *crowd, *sparse],
        DJControls(start_path="/anchor.flac"),
        30,
        spread_energy=True,
    )

    assert pool[0].path == "/anchor.flac"
    assert {4, 9} <= _energy_levels(pool), sorted(_energy_levels(pool))


def test_energy_spread_is_off_by_default() -> None:
    """Strategies that hold one level must not be handed a spread pool."""
    anchor = track("/anchor.flac", energy_level=7)
    crowd = [track(f"/same{index}.flac", energy_level=7) for index in range(60)]
    sparse = [track(f"/low{index}.flac", energy_level=2) for index in range(5)]

    pool = build_recommendation_pool([anchor, *crowd, *sparse], DJControls(start_path="/anchor.flac"), 20)

    assert _energy_levels(pool) == {7}


def test_half_time_candidate_lands_in_closest_bpm_bucket() -> None:
    anchor = track("/anchor.flac").model_copy(update={"bpm": 84.6})
    candidate = track("/candidate.flac").model_copy(update={"bpm": 169.0})

    similarity_key = _track_similarity_key(set(), [anchor], candidate)

    assert similarity_key[0] == 0


def test_diagonal_key_reaches_default_pool_despite_adjacent_key_crowd() -> None:
    anchor = track("/anchor.flac").model_copy(update={"camelot_key": "7A"})
    diagonal = track("/00-diagonal.flac").model_copy(update={"camelot_key": "8B"})
    adjacent = [track(f"/adjacent-{index:02d}.flac").model_copy(update={"camelot_key": "8A"}) for index in range(25)]

    pool = build_recommendation_pool(
        [anchor, *adjacent, diagonal],
        DJControls(start_path=anchor.path),
    )

    assert diagonal in pool


def test_candidate_pool_orders_camelot_score_bands() -> None:
    anchor = track("/anchor.flac").model_copy(update={"camelot_key": "7A"})
    candidates = [
        track("/a-same.flac").model_copy(update={"camelot_key": "7A"}),
        track("/b-diagonal.flac").model_copy(update={"camelot_key": "8B"}),
        track("/c-relative.flac").model_copy(update={"camelot_key": "7B"}),
        track("/d-energy-boost.flac").model_copy(update={"camelot_key": "9A"}),
        track("/e-semitone-lift.flac").model_copy(update={"camelot_key": "2A"}),
        track("/f-incompatible.flac").model_copy(update={"camelot_key": "11B"}),
        track("/g-no-key.flac").model_copy(update={"camelot_key": None}),
    ]

    pool = build_recommendation_pool(
        [anchor, *reversed(candidates)],
        DJControls(start_path=anchor.path),
    )

    assert pool == [anchor, *candidates]


def test_candidate_without_camelot_key_sorts_last_but_remains_in_pool() -> None:
    anchor = track("/anchor.flac").model_copy(update={"camelot_key": "7A"})
    no_key = track("/a-no-key.flac").model_copy(update={"camelot_key": None})
    incompatible = track("/z-incompatible.flac").model_copy(update={"camelot_key": "11B"})

    pool = build_recommendation_pool(
        [anchor, no_key, incompatible],
        DJControls(start_path=anchor.path),
    )

    assert pool == [anchor, incompatible, no_key]


def test_candidate_pool_default_limit_remains_unchanged() -> None:
    anchor = track("/anchor.flac")
    candidates = [track(f"/candidate-{index:02d}.flac") for index in range(30)]

    pool = build_recommendation_pool(
        [anchor, *candidates],
        DJControls(start_path=anchor.path),
    )

    assert len(pool) == 25


def test_energy_spread_still_fills_the_pool() -> None:
    """Spreading must not shrink the pool the optimizer gets."""
    anchor = track("/anchor.flac", energy_level=6)
    crowd = [track(f"/t{index}.flac", energy_level=5 + index % 4) for index in range(100)]

    pool = build_recommendation_pool([anchor, *crowd], DJControls(start_path="/anchor.flac"), 40, spread_energy=True)

    assert len(pool) == 40


def test_protected_anchor_never_displaces_a_control_track() -> None:
    """Anchor retention must never cost a control its slot.

    Controls MUST remain present in their existing positions. When the pool has
    no trimmable (non-control) slot, displacing "the last slot" evicts a control
    and `apply_controls` then rejects the whole request downstream. Not retaining
    the anchor is the honest outcome -- the colour gate already fails closed on a
    missing anchor.
    """
    controls = DJControls(start_path="/start.flac", end_path="/end.flac", locked_paths={"/locked.flac"})
    records = [track("/start.flac"), track("/end.flac"), track("/locked.flac"), track("/anchor.flac")]

    pool = build_recommendation_pool(records, controls, 3, protected_path="/anchor.flac")

    assert {item.path for item in pool} == {"/start.flac", "/end.flac", "/locked.flac"}


# ---------------------------------------------------------------------------
# Opt-in familiarity preference signal (Plan 3 T3).
#
# Contract: INERT by default (None signals or weight 0 -> byte-identical
# behavior); when opted in, a bounded boost only REORDERS candidates within
# one similarity class — it never changes pool membership, so familiarity
# never blocks a track.
# ---------------------------------------------------------------------------


def _familiarity_pool_records() -> list[TrackRecord]:
    """Anchor + 25 tag-identical candidates ranked purely by path tiebreak.

    With identical bpm/key/energy/tags every similarity key ties except the
    final path component, so the baseline rank order is exactly the path
    order: /t01 .. /t24, then /z_familiar last.
    """
    anchor = track("/anchor.flac")
    others = [track(f"/t{index:02d}.flac") for index in range(1, 25)]
    return [anchor, *others, track("/z_familiar.flac")]


def _familiarity_signals() -> dict:
    from xfinaudio.recommendation.familiarity import FamiliaritySignal

    return {"/z_familiar.flac": FamiliaritySignal(play_count=10, last_played=None, crate_count=1)}


def test_familiarity_signals_with_zero_weight_are_identity():
    records = _familiarity_pool_records()
    controls = DJControls(start_path="/anchor.flac")
    baseline = build_recommendation_pool(records, controls, 40)
    inert = build_recommendation_pool(records, controls, 40, familiarity=_familiarity_signals(), familiarity_weight=0.0)

    assert [r.path for r in inert] == [r.path for r in baseline]


def test_empty_familiarity_mapping_with_positive_weight_is_identity():
    records = _familiarity_pool_records()
    controls = DJControls(start_path="/anchor.flac")
    baseline = build_recommendation_pool(records, controls, 40)
    inert = build_recommendation_pool(records, controls, 40, familiarity={}, familiarity_weight=1.0)

    assert [r.path for r in inert] == [r.path for r in baseline]


def test_familiarity_weight_reorders_candidates_within_similarity_class():
    records = _familiarity_pool_records()
    controls = DJControls(start_path="/anchor.flac")
    baseline = build_recommendation_pool(records, controls, 40)
    assert baseline[-1].path == "/z_familiar.flac"  # pre-condition: ranked last by path tiebreak

    boosted = build_recommendation_pool(
        records, controls, 40, familiarity=_familiarity_signals(), familiarity_weight=1.0
    )

    # With 25 ranked candidates the base rank fraction drops by 1/25 per rank,
    # so the capped 5% boost lifts the familiar track exactly one position.
    assert boosted[-2].path == "/z_familiar.flac"
    assert boosted[-1].path == "/t24.flac"


def test_familiarity_boost_is_capped_at_five_percent_of_score_range():
    records = _familiarity_pool_records()
    controls = DJControls(start_path="/anchor.flac")

    uncapped_would_win = build_recommendation_pool(
        records, controls, 40, familiarity=_familiarity_signals(), familiarity_weight=100.0
    )

    # Uncapped, a weight of 100 would carry the familiar track to the top of
    # the pool; capped at 5% of the [0, 1] score range it climbs one rank.
    assert uncapped_would_win[1].path == "/t01.flac"
    assert uncapped_would_win[-2].path == "/z_familiar.flac"


def test_familiarity_never_changes_pool_membership():
    records = _familiarity_pool_records()
    controls = DJControls(start_path="/anchor.flac")
    baseline = build_recommendation_pool(records, controls, 40)
    boosted = build_recommendation_pool(
        records, controls, 40, familiarity=_familiarity_signals(), familiarity_weight=1.0
    )

    assert {r.path for r in boosted} == {r.path for r in baseline}


def test_familiarity_ignores_signals_for_paths_outside_the_pool():
    records = _familiarity_pool_records()
    controls = DJControls(start_path="/anchor.flac")
    baseline = build_recommendation_pool(records, controls, 40)
    signals = {"/not-in-pool.flac": _familiarity_signals()["/z_familiar.flac"]}

    boosted = build_recommendation_pool(records, controls, 40, familiarity=signals, familiarity_weight=1.0)

    assert [r.path for r in boosted] == [r.path for r in baseline]


# ---------------------------------------------------------------------------
# Engine pack slice 2 (T1 triads/tandas) — reserved `triad:` tag namespace.
#
# A triad is a short cluster of tracks the DJ rehearsed together. Its provenance
# rides the existing tag channel under a reserved prefix; the suffix after the
# prefix is the shared identity. The parser is the only new data contract, and it
# is purely additive: Mixed In Key tags flow through the tag channel untouched.
# ---------------------------------------------------------------------------


def _tagged(path: str, *tags: str) -> TrackRecord:
    return track(path).model_copy(update={"tags": list(tags)})


def test_triad_identities_parses_the_reserved_prefix() -> None:
    assert track_triad_identities(_tagged("/t.flac", "triad:a7f3")) == frozenset({"a7f3"})


def test_triad_prefix_match_is_case_insensitive_and_casefolds_the_identity() -> None:
    record = _tagged("/t.flac", "TRIAD:A7F3", "Triad:AbC")

    assert track_triad_identities(record) == frozenset({"a7f3", "abc"})


def test_triad_identities_collects_every_identity_a_track_carries() -> None:
    record = _tagged("/t.flac", "triad:alpha", "peak", "triad:beta")

    assert track_triad_identities(record) == frozenset({"alpha", "beta"})


def test_track_without_triad_tags_has_no_triad_identity() -> None:
    assert track_triad_identities(track("/t.flac")) == frozenset()


def test_triad_identity_requires_a_non_empty_suffix() -> None:
    """`triad:` alone names no cluster, so it is malformed and ignored.

    The prefix alone (or with only whitespace after it) carries no identity to
    share: treating it as one would make every such track "rehearsed together".
    """
    record = _tagged("/t.flac", "triad:", "triad:   ", "triad")

    assert track_triad_identities(record) == frozenset()


def test_triad_identity_tolerates_surrounding_whitespace() -> None:
    assert track_triad_identities(_tagged("/t.flac", "  triad:a7f3  ")) == frozenset({"a7f3"})


def test_triad_identity_is_read_from_tags_only_never_from_genre() -> None:
    """The reserved namespace is a TAG convention: genre text is never provenance.

    Genre is a comma-joined free-text field the scanner also splits into vibe
    terms; reading it as provenance would let ordinary genre text create triads.
    """
    record = track("/t.flac").model_copy(update={"tags": [], "genre": "triad:a7f3"})

    assert track_triad_identities(record) == frozenset()


def test_triad_identity_helper_is_part_of_the_candidate_pool_api() -> None:
    assert "track_triad_identities" in candidate_pool.__all__


def test_dedupe_keeps_distinct_songs_that_share_a_triad_identity() -> None:
    """A triad groups DIFFERENT songs; dedupe collapses duplicate VERSIONS.

    Membership in a triad is never a cross-song grouping key: the grouping key
    stays title+artist, so every member of a triad survives candidate-pool
    dedupe and only true duplicate versions collapse.
    """
    first = _record("/triad-one.mp3", title="Song One", artist="Artist A").model_copy(update={"tags": ["triad:a7f3"]})
    second = _record("/triad-two.mp3", title="Song Two", artist="Artist B").model_copy(update={"tags": ["triad:a7f3"]})

    result = dedupe_recommendation_duplicates([first, second], controls=None)

    assert [r.path for r in result] == ["/triad-one.mp3", "/triad-two.mp3"]


def test_build_recommendation_pool_membership_and_order_ignore_triad_tags() -> None:
    """Slice-2 decision: the pool seam is deliberately untouched.

    The triad bonus is priced in `score_transition`, so it reaches ordering
    through the optimizer's objective — where it can perturb which adjacency is
    chosen but can never change pool membership. Pool ranking stays exactly as
    it is today, and triad tags are inert here.
    """
    anchor = track("/anchor.flac")
    plain = [track(f"/c{index:02d}.flac") for index in range(5)]
    tagged = [r.model_copy(update={"tags": [*r.tags, "triad:alpha"]}) for r in plain]

    baseline = build_recommendation_pool([anchor, *plain], DJControls(start_path="/anchor.flac"), 10)
    with_triads = build_recommendation_pool([anchor, *tagged], DJControls(start_path="/anchor.flac"), 10)

    assert [r.path for r in with_triads] == [r.path for r in baseline]
