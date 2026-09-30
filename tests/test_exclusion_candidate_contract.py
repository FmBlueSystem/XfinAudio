"""Hard exclusions act before anchor selection, dedupe, and candidate caps."""

from xfinaudio.application.recommendation_candidates import (
    plan_recommendation_candidate_context,
    plan_recommendation_candidates,
)
from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist


def track(path: str, blue: bool = False) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        artist="artist",
        bpm=120,
        camelot_key="8A",
        energy_level=5,
        genre="House",
        metadata_status="complete",
        spectral_profile=SpectralProfile(
            red_ratio=0 if blue else 1,
            green_ratio=0,
            blue_ratio=1 if blue else 0,
            centroid_hz=1000,
            rolloff_hz=2000,
            dominant_color="BLUE" if blue else "RED",
        ),
    )


def test_excluded_tracks_do_not_spend_build_pool_slots() -> None:
    pool = [track(f"{i:02}") for i in range(10)]
    result = plan_recommendation_candidates(
        scanned_records=pool,
        controls=DJControls(excluded_paths={t.path for t in pool[:5]}),
        limit=3,
        strategy_name="harmonic_journey",
    )
    assert len(result) == 3
    assert {t.path for t in result}.isdisjoint({t.path for t in pool[:5]})


def test_excluded_record_cannot_become_implicit_color_anchor() -> None:
    pool = [track("a-excluded"), track("blue1", True), track("blue2", True)]
    controls = DJControls(excluded_paths={"a-excluded"})
    context = plan_recommendation_candidate_context(
        scanned_records=pool, controls=controls, limit=5, strategy_name="same_color"
    )
    assert context.color_anchor_path == "blue1"
    assert {t.path for t in context.records} == {"blue1", "blue2"}
    result = recommend_playlist(pool, "same_color", controls, target_count=2)
    assert {t.path for t in result.ordered_tracks} == {"blue1", "blue2"}


def test_excluded_duplicate_cannot_suppress_eligible_version() -> None:
    pool = [track("a").model_copy(update={"title": "Song"}), track("b").model_copy(update={"title": "Song (Edit)"})]
    result = plan_recommendation_candidates(scanned_records=pool, controls=DJControls(excluded_paths={"a"}), limit=5)
    assert [t.path for t in result] == ["b"]


def test_manual_exclusion_wins_without_becoming_unknown_control_error() -> None:
    controls = DJControls(manual_order_paths=["a", "b"], excluded_paths={"a"})
    result = recommend_playlist([track(c) for c in "abc"], "harmonic_journey", controls, target_count=2)
    assert [t.path for t in result.ordered_tracks] == ["b", "c"]


def test_illegal_manual_arc_prefix_fails_closed_with_explicit_reason() -> None:
    pool = [
        track("a").model_copy(update={"bpm": 60}),
        track("b").model_copy(update={"bpm": 90}),
        track("c").model_copy(update={"bpm": 90}),
    ]
    result = recommend_playlist(pool, "harmonic_journey", DJControls(manual_order_paths=["a", "b"]), target_count=3)
    assert not result.ordered_tracks
    assert any("manual" in text.lower() and "BPM" in text for text in result.warnings)
