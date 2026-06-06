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


def test_prep_copilot_surfaces_blocked_variant_when_required_track_breaks_bpm_gate() -> None:
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

    assert any(variant.readiness.status == "blocked" for variant in plan.variants)
    assert any("BPM continuity" in blocker for variant in plan.variants for blocker in variant.blockers)
