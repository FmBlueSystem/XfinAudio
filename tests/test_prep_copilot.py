from typing import Any

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan


def track(
    path: str,
    *,
    bpm: float = 120.0,
    key: str = "8A",
    energy: int = 5,
    genre: str = "House",
    tags: list[str] | None = None,
    status: str = "complete",
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path.rsplit("/", maxsplit=1)[-1],
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
    assert all(variant.readiness.status == "ready" for variant in plan.variants)


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


def test_prep_copilot_surfaces_review_variant_when_required_track_breaks_bpm_gate() -> None:
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

    assert any(variant.readiness.status == "needs_review" for variant in plan.variants)
    assert any(
        check.label == "BPM continuity" and check.status == "needs_review"
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
