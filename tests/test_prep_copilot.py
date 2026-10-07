from typing import Any

import pytest
from pydantic import ValidationError

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.prep_copilot import (
    PREP_PLAYED_SECONDS_PER_TRACK,
    DJSetIntent,
    build_prep_copilot_plan,
)


def track(
    path: str,
    *,
    bpm: float = 120.0,
    key: str = "8A",
    energy: int = 5,
    genre: str = "House",
    tags: list[str] | None = None,
    status: str = "complete",
    duration: float | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path.rsplit("/", maxsplit=1)[-1],
        duration=duration,
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        genre=genre,
        tags=[genre] if tags is None else tags,
        metadata_status=status,  # type: ignore[arg-type]
    )


def spectral_track(
    path: str,
    color: ColorName,
    *,
    genre: str,
    bpm: float = 120.0,
    key: str = "8A",
    energy: int = 5,
) -> TrackRecord:
    return track(path, bpm=bpm, key=key, energy=energy, genre=genre).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=1.0 if color == "RED" else 0.0,
                green_ratio=1.0 if color == "GREEN" else 0.0,
                blue_ratio=1.0 if color == "BLUE" else 0.0,
                # Finite positive centroid/rolloff so same-label candidates share the
                # gate's relative-delta denominators and pass the bounded proximity gate.
                centroid_hz=1000.0,
                rolloff_hz=2000.0,
                dominant_color=color,
            )
        }
    )


def test_prep_copilot_returns_three_comparable_variants_with_same_intent() -> None:
    tracks = [
        track("/music/start.flac", bpm=120, key="8A", energy=4, genre="House"),
        track("/music/groove.flac", bpm=121, key="8A", energy=5, genre="House"),
        track("/music/lift.flac", bpm=122, key="9A", energy=6, genre="House"),
        track("/music/peak.flac", bpm=123, key="9A", energy=7, genre="House"),
    ]
    intent = DJSetIntent(
        name="Saturday warmup",
        strategy="build",
        start_path="/music/start.flac",
        target_track_count=3,
        genre_focus="House",
    )

    plan = build_prep_copilot_plan(tracks, intent)

    assert [variant.name for variant in plan.variants] == ["safe", "balanced", "adventurous"]
    assert plan.intent == intent
    assert all(variant.recommendation.ordered_tracks[0].path == "/music/start.flac" for variant in plan.variants)
    assert all(len(variant.recommendation.ordered_tracks) <= 3 for variant in plan.variants)
    # The arc now spans the requested three tracks rather than a larger pool
    # later prefix-trimmed to three. Reaching E7 from E4 needs a two-level seam.
    assert all(variant.readiness.status == "needs_review" for variant in plan.variants)
    assert all(
        any(
            check.label == "Continuidad de energía" and check.status == "needs_review"
            for check in variant.readiness.checks
        )
        for variant in plan.variants
    )


def test_prep_copilot_wide_library_does_not_collapse_every_variant_to_one_track() -> None:
    anchor = track("/music/anchor.flac", bpm=128, key="8A", energy=5, genre="House")
    scattered_bpms = [60 * 1.04**index for index in range(30)]
    scattered = [
        track(f"/music/scattered-{index}.flac", bpm=bpm, key="8A", energy=5, genre="House")
        for index, bpm in enumerate(scattered_bpms)
        if not 124 <= bpm <= 132
    ]
    bridge = [
        track(f"/music/bridge-{index}.flac", bpm=60 + index * 0.7, key="8A", energy=5, genre="House")
        for index in range(160)
    ]
    anchor_cluster = [
        track(f"/music/cluster-{index}.flac", bpm=127 + index % 3, key="8A", energy=5, genre="House")
        for index in range(40)
    ]
    intent = DJSetIntent(
        name="Wide library",
        strategy="harmonic_journey",
        start_path=anchor.path,
        target_track_count=25,
        genre_focus="House",
    )

    plan = build_prep_copilot_plan([anchor, *scattered, *bridge, *anchor_cluster], intent)

    assert all(len(variant.recommendation.ordered_tracks) >= 10 for variant in plan.variants)
    assert all(len(variant.recommendation.ordered_tracks) <= intent.target_track_count for variant in plan.variants)
    assert all(variant.recommendation.ordered_tracks[0].path == anchor.path for variant in plan.variants)


def test_prep_copilot_tiny_library_returns_available_tracks_without_raising() -> None:
    tracks = [
        track("/music/anchor.flac", bpm=128),
        track("/music/two.flac", bpm=128),
        track("/music/three.flac", bpm=129),
    ]
    intent = DJSetIntent(
        name="Tiny library",
        strategy="harmonic_journey",
        start_path=tracks[0].path,
        target_track_count=25,
    )

    plan = build_prep_copilot_plan(tracks, intent)

    assert all(len(variant.recommendation.ordered_tracks) == len(tracks) for variant in plan.variants)


def test_safe_variant_keeps_focused_genre_while_adventurous_can_bridge_outside_it() -> None:
    tracks = [
        track("/music/start.flac", bpm=100, key="8A", energy=4, genre="Disco"),
        track("/music/disco.flac", bpm=102, key="8A", energy=5, genre="Disco"),
        track("/music/funk.flac", bpm=103, key="9A", energy=6, genre="Funk", tags=["Funk", "Disco"]),
        track("/music/rock.flac", bpm=104, key="9A", energy=6, genre="Rock", tags=["Guitar"]),
    ]
    intent = DJSetIntent(
        name="Disco bridge",
        strategy="harmonic_journey",
        start_path="/music/start.flac",
        target_track_count=4,
        genre_focus="Disco",
    )

    plan = build_prep_copilot_plan(tracks, intent)
    by_name = {variant.name: variant for variant in plan.variants}

    safe_genres = {track.genre for track in by_name["safe"].recommendation.ordered_tracks}
    adventurous_genres = {track.genre for track in by_name["adventurous"].recommendation.ordered_tracks}

    assert safe_genres <= {"Disco"}
    assert "Funk" in adventurous_genres
    assert any("genre focus" in warning for warning in by_name["adventurous"].warnings)


def test_variant_genre_focus_matches_case_insensitively() -> None:
    """ "classical" focus must match "Classical" tracks under the shared genre contract.

    The old variant filter used case-sensitive equality, so a lowercase focus
    matched zero tracks and the pool silently collapsed to the protected anchor
    even though the Build genre prefilter (casefolded) matched the same library.
    """
    tracks = [
        track("/music/start.flac", bpm=120, key="8A", energy=4, genre="Classical"),
        track("/music/sonata.flac", bpm=121, key="8A", energy=5, genre="Classical"),
    ]
    intent = DJSetIntent(
        name="Lowercase focus",
        strategy="build",
        start_path="/music/start.flac",
        target_track_count=2,
        genre_focus="classical",
    )

    plan = build_prep_copilot_plan(tracks, intent)

    safe_paths = {t.path for t in plan.variants[0].recommendation.ordered_tracks}
    assert "/music/sonata.flac" in safe_paths


def test_variant_genre_focus_zero_match_falls_back_to_pool_with_warning() -> None:
    """A genre focus matching zero tracks must fall back to the pool, not protected paths.

    The old contract shrank the variant pool to protected paths only (the anchor
    when nothing else was selected) with no explanation. The shared contract now
    falls back to the incoming pool with a warning, like the genre prefilter does.
    """
    tracks = [
        track("/music/start.flac", bpm=120, key="8A", energy=4, genre="House"),
        track("/music/groove.flac", bpm=121, key="8A", energy=5, genre="House"),
    ]
    intent = DJSetIntent(
        name="Empty focus",
        strategy="build",
        start_path="/music/start.flac",
        target_track_count=2,
        genre_focus="Trance",
    )

    plan = build_prep_copilot_plan(tracks, intent)

    safe = plan.variants[0]
    assert len(safe.recommendation.ordered_tracks) == 2
    assert any("Trance" in warning and "match" in warning.casefold() for warning in safe.warnings)


def test_pool_notes_record_how_the_variant_pool_shrank() -> None:
    """Every variant must carry per-step pool diagnostics: incoming size, filter
    result, and BPM-gate drops reused from the existing recommendation warnings.
    """
    anchor = track("/music/anchor.flac", bpm=87.47, key="8A", energy=3, genre="Classical")
    scattered = [
        track(f"/music/c{index}.flac", bpm=bpm, key="8A", energy=3, genre="Classical")
        for index, bpm in enumerate([62.0, 70.5, 76.0, 96.0, 108.0, 120.0, 128.0, 136.5, 174.0])
    ]
    intent = DJSetIntent(
        name="Scattered classical",
        strategy="harmonic_journey",
        start_path=anchor.path,
        target_track_count=25,
        genre_focus="Classical",
    )

    plan = build_prep_copilot_plan([anchor, *scattered], intent)

    assert len(plan.variants[0].recommendation.ordered_tracks) <= 1
    for variant in plan.variants:
        assert variant.pool_notes, "pool notes must explain how the pool was built"
        assert variant.pool_notes[0] == "Incoming pool: 10 track(s)"
        assert any("Genre focus 'Classical'" in note for note in variant.pool_notes)
    gated = [variant for variant in plan.variants if any("BPM vecinos" in warning for warning in variant.warnings)]
    assert gated, "scattered BPMs must exercise the adjacency gate"
    for variant in gated:
        assert any("BPM vecinos" in note for note in variant.pool_notes)


def test_pool_notes_warn_when_variant_collapses_to_the_anchor() -> None:
    """A variant that keeps at most the anchor from a larger pool says why it collapsed."""
    anchor = track("/music/anchor.flac", bpm=87.47, key="8A", energy=3, genre="Classical")
    scattered = [
        track(f"/music/c{index}.flac", bpm=bpm, key="8A", energy=3, genre="Classical")
        for index, bpm in enumerate([62.0, 70.5, 76.0, 96.0, 108.0, 120.0, 128.0, 136.5, 174.0])
    ]
    intent = DJSetIntent(
        name="Scattered classical",
        strategy="harmonic_journey",
        start_path=anchor.path,
        target_track_count=25,
        genre_focus="Classical",
    )

    plan = build_prep_copilot_plan([anchor, *scattered], intent)

    collapsed = [
        variant
        for variant in plan.variants
        if len(variant.recommendation.ordered_tracks) <= 1 and len(variant.pool_notes) >= 1
    ]
    assert collapsed, "the scattered-BPM library must collapse at least one variant"
    for variant in collapsed:
        assert any("only the anchor" in warning.casefold() for warning in variant.warnings)
        assert any("only the anchor" in note.casefold() for note in variant.pool_notes)


def test_pool_notes_do_not_warn_when_variant_simply_meets_the_requested_cap() -> None:
    """Hitting the requested track count is the cap working, not a pool collapse."""
    tracks = [track(f"/music/t{index}.flac", bpm=120 + index, key="8A", energy=5, genre="House") for index in range(6)]
    intent = DJSetIntent(
        name="Small cap",
        strategy="build",
        start_path="/music/t0.flac",
        target_track_count=2,
        genre_focus="House",
    )

    plan = build_prep_copilot_plan(tracks, intent)

    for variant in plan.variants:
        assert len(variant.recommendation.ordered_tracks) == 2
        assert not any("only the anchor" in warning.casefold() for warning in variant.warnings)


def test_prep_copilot_blocks_variant_when_required_track_breaks_bpm_gate() -> None:
    tracks = [
        track("/music/start.flac", bpm=100, key="8A", energy=4, genre="House"),
        track("/music/required.flac", bpm=110, key="8A", energy=5, genre="House"),
    ]
    intent = DJSetIntent(
        name="Impossible request",
        strategy="harmonic_journey",
        start_path="/music/start.flac",
        required_paths=["/music/required.flac"],
        target_track_count=2,
        genre_focus="House",
    )

    plan = build_prep_copilot_plan(tracks, intent)

    assert all(variant.readiness.status == "blocked" for variant in plan.variants)
    assert any(
        check.label == "Continuidad de BPM" and check.status == "blocked"
        for variant in plan.variants
        for check in variant.readiness.checks
    )


def test_variant_that_filters_out_the_bound_colour_anchor_fails_closed() -> None:
    """A genre-focused variant that loses the bound anchor must not rebind a different one.

    The anchor identity is bound once by the candidate-planning seam. When a variant's
    genre filter removes that exact track, the colour gate has to fail closed instead of
    silently re-resolving another anchor and gating the DJ's set against a wrong colour.
    """
    tracks = [
        spectral_track("/music/anchor.flac", "RED", genre="Techno", bpm=124, key="8A", energy=6),
        spectral_track("/music/house-a.flac", "GREEN", genre="House", bpm=122, key="8A", energy=5),
        spectral_track("/music/house-b.flac", "GREEN", genre="House", bpm=123, key="9A", energy=6),
    ]
    intent = DJSetIntent(
        name="Colour prep",
        strategy="same_color",
        target_track_count=3,
        genre_focus="House",
    )

    plan = build_prep_copilot_plan(tracks, intent, color_anchor_path="/music/anchor.flac")
    by_name = {variant.name: variant for variant in plan.variants}

    safe = by_name["safe"]
    assert safe.recommendation.ordered_tracks == []
    assert any("anchor is missing" in warning for warning in safe.warnings)
    # The variant that keeps the anchor still gates against it: only its RED colour.
    adventurous = by_name["adventurous"]
    assert [item.path for item in adventurous.recommendation.ordered_tracks] == ["/music/anchor.flac"]


def test_same_color_energy_variant_that_filters_out_the_bound_anchor_fails_closed() -> None:
    """The exact-energy colour gate must fail closed on the same variant filter as `same_color`.

    `same_color_energy` runs the same bound-anchor contract plus one extra predicate:
    the candidate must share the anchor's exact energy level. The pool below makes that
    predicate load-bearing — one candidate matches the anchor's colour but not its
    energy, the other matches its energy but not its colour — so an anchor-keeping
    variant proves the gate really is anchored, not merely non-empty.
    """
    tracks = [
        spectral_track("/music/anchor.flac", "RED", genre="Techno", bpm=124, key="8A", energy=6),
        spectral_track("/music/house-red.flac", "RED", genre="House", bpm=122, key="8A", energy=8),
        spectral_track("/music/house-green.flac", "GREEN", genre="House", bpm=123, key="9A", energy=6),
    ]
    intent = DJSetIntent(
        name="Colour and energy prep",
        strategy="same_color_energy",
        target_track_count=3,
        genre_focus="House",
    )

    plan = build_prep_copilot_plan(tracks, intent, color_anchor_path="/music/anchor.flac")
    by_name = {variant.name: variant for variant in plan.variants}

    safe = by_name["safe"]
    assert safe.recommendation.ordered_tracks == []
    assert any("anchor is missing" in warning for warning in safe.warnings)
    # The variant that keeps the anchor gates against it on BOTH axes: neither the
    # same-colour/wrong-energy nor the same-energy/wrong-colour candidate survives.
    adventurous = by_name["adventurous"]
    assert [item.path for item in adventurous.recommendation.ordered_tracks] == ["/music/anchor.flac"]


def test_build_prep_copilot_plan_forwards_the_bound_anchor_to_every_variant(monkeypatch) -> None:
    from xfinaudio.recommendation import prep_copilot as prep_copilot_module

    real_recommend_playlist = prep_copilot_module.recommend_playlist
    forwarded: list[str | None] = []

    def recording_recommend_playlist(*args: Any, **kwargs: Any) -> Any:
        forwarded.append(kwargs.get("color_anchor_path"))
        return real_recommend_playlist(*args, **kwargs)

    monkeypatch.setattr(prep_copilot_module, "recommend_playlist", recording_recommend_playlist)

    tracks = [
        spectral_track("/music/anchor.flac", "GREEN", genre="House", bpm=122, key="8A", energy=5),
        spectral_track("/music/green.flac", "GREEN", genre="House", bpm=123, key="9A", energy=6),
    ]
    intent = DJSetIntent(name="Colour prep", strategy="same_color", target_track_count=2)

    build_prep_copilot_plan(tracks, intent, color_anchor_path="/music/anchor.flac")

    assert forwarded == ["/music/anchor.flac", "/music/anchor.flac", "/music/anchor.flac"]


def test_pool_notes_carry_the_upstream_prefilter_preamble_first() -> None:
    """A prefilter that ran before the plan must still lead the pool notes."""
    tracks = [track(f"/music/t{index}.flac", bpm=120 + index, genre="Disco") for index in range(4)]
    intent = DJSetIntent(
        name="Prefiltered",
        strategy="build",
        target_track_count=3,
        pool_note_preamble="Genre 'Disco' prefilter: 4 of 63 complete library track(s)",
    )

    plan = build_prep_copilot_plan(tracks, intent)

    for variant in plan.variants:
        assert variant.pool_notes[0] == "Genre 'Disco' prefilter: 4 of 63 complete library track(s)"
        assert variant.pool_notes[1] == f"Incoming pool: {len(tracks)} track(s)"


# ---------------------------------------------------------------------------
# T3 -- runtime budgeting. The booked slot is the planning input; track count
# is a number the DJ derives from it, not the other way round.
# ---------------------------------------------------------------------------


def _slot_tracks(count: int = 20, *, duration: float = 300.0) -> list[TrackRecord]:
    return [
        track(f"/music/slot{index:02d}.flac", bpm=120.0 + index * 0.3, energy=5, duration=duration)
        for index in range(count)
    ]


def test_intent_target_minutes_sizes_every_variant_by_runtime() -> None:
    """A 20-minute slot of 300s tracks is ten two-minute segments each.

    ``target_track_count`` is left at its default so it cannot be the binding
    constraint: the minutes budget alone has to produce the ten-track set.
    """
    tracks = _slot_tracks()
    intent = DJSetIntent(name="Slot", strategy="harmonic_journey", target_minutes=20.0)

    plan = build_prep_copilot_plan(tracks, intent)

    for variant in plan.variants:
        kept = variant.recommendation.ordered_tracks
        assert len(kept) == 10, variant.name
        played = sum(min(item.duration or 0.0, PREP_PLAYED_SECONDS_PER_TRACK) for item in kept)
        assert played <= 20 * 60, variant.name


def test_intent_minutes_budget_wins_for_sizing_and_count_stays_a_hard_cap() -> None:
    """With both set, minutes size the set and the count can only cut it down."""
    tracks = _slot_tracks()

    minutes_sized = build_prep_copilot_plan(
        tracks,
        DJSetIntent(name="Slot", strategy="harmonic_journey", target_minutes=20.0, target_track_count=25),
    )
    for variant in minutes_sized.variants:
        assert len(variant.recommendation.ordered_tracks) == 10, variant.name

    capped = build_prep_copilot_plan(
        tracks,
        DJSetIntent(name="Slot", strategy="harmonic_journey", target_minutes=60.0, target_track_count=3),
    )
    for variant in capped.variants:
        assert len(variant.recommendation.ordered_tracks) == 3, variant.name


def test_intent_target_minutes_is_optional_and_bounded() -> None:
    assert DJSetIntent(name="No slot").target_minutes is None
    assert DJSetIntent(name="Ten hours", target_minutes=600.0).target_minutes == 600.0


@pytest.mark.parametrize("value", [0.0, -1.0, 601.0])
def test_intent_target_minutes_must_fit_a_real_slot(value: float) -> None:
    with pytest.raises(ValidationError):
        DJSetIntent(name="Bad slot", target_minutes=value)


# ---------------------------------------------------------------------------
# T4 -- slot role decoupled from the ordering strategy. The strategy still
# weights and orders; the slot role names the energy shape traced underneath.
# ---------------------------------------------------------------------------


def test_intent_forwards_target_minutes_and_slot_role_to_every_variant(monkeypatch: Any) -> None:
    from xfinaudio.recommendation import prep_copilot as prep_copilot_module

    real_recommend_playlist = prep_copilot_module.recommend_playlist
    forwarded: list[dict[str, Any]] = []

    def recording_recommend_playlist(*args: Any, **kwargs: Any) -> Any:
        forwarded.append(kwargs)
        return real_recommend_playlist(*args, **kwargs)

    monkeypatch.setattr(prep_copilot_module, "recommend_playlist", recording_recommend_playlist)

    intent = DJSetIntent(
        name="Peak slot",
        strategy="harmonic_journey",
        target_minutes=20.0,
        slot_role="peak_time",
    )

    build_prep_copilot_plan(_slot_tracks(), intent)

    assert [call["target_duration_minutes"] for call in forwarded] == [20.0, 20.0, 20.0]
    assert [call["played_seconds_per_track"] for call in forwarded] == [PREP_PLAYED_SECONDS_PER_TRACK] * 3
    assert [call["arc_strategy"] for call in forwarded] == ["peak_time", "peak_time", "peak_time"]


def test_intent_without_slot_or_minutes_forwards_neutral_defaults(monkeypatch: Any) -> None:
    """Older intents keep today's behavior: no runtime cap, no arc override."""
    from xfinaudio.recommendation import prep_copilot as prep_copilot_module

    real_recommend_playlist = prep_copilot_module.recommend_playlist
    forwarded: list[dict[str, Any]] = []

    def recording_recommend_playlist(*args: Any, **kwargs: Any) -> Any:
        forwarded.append(kwargs)
        return real_recommend_playlist(*args, **kwargs)

    monkeypatch.setattr(prep_copilot_module, "recommend_playlist", recording_recommend_playlist)

    build_prep_copilot_plan(_slot_tracks(6), DJSetIntent(name="Plain", strategy="harmonic_journey"))

    assert [call["target_duration_minutes"] for call in forwarded] == [None, None, None]
    assert [call["played_seconds_per_track"] for call in forwarded] == [None, None, None]
    assert [call["arc_strategy"] for call in forwarded] == [None, None, None]
