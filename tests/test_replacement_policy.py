"""Direct backfill must retain resolved generation policy, not guess it anew."""

import pytest

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.loudness_policy import LoudnessBand
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    recommend_playlist,
    recommendation_reordered,
    recommendation_with_replacement,
    recommendation_without_paths,
)


def _track(path: str, energy: int = 5, genre: str = "House", bpm: float = 117) -> TrackRecord:
    return TrackRecord(
        path=path, energy_level=energy, genre=genre, bpm=bpm, camelot_key="8A", metadata_status="complete"
    )


def _color(path: str, red: float = 0.8, energy: int = 5) -> TrackRecord:
    return _track(path, energy).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=red,
                green_ratio=1 - red,
                blue_ratio=0,
                centroid_hz=1000,
                rolloff_hz=2000,
                dominant_color="RED",
            )
        }
    )


def _loud(path: str, lufs: float) -> TrackRecord:
    return _track(path).model_copy(
        update={
            "loudness_profile": LoudnessProfile(
                lufs_integrated=lufs,
                loudness_range_lra=2,
                true_peak_dbtp=-1,
                status=LoudnessStatus.MEASURED,
                engine_fingerprint="synthetic",
            )
        }
    )


@pytest.mark.parametrize(
    "strategy,energy,bad_energy,bad_bpm",
    [
        ("same_energy", 5, 10, 117),
        ("warmup", 5, 7, 117),
        ("peak_time", 8, 6, 117),
        ("chill", 5, 6, 117),
        ("chill", 5, 5, 119),
    ],
)
def test_direct_backfill_enforces_strategy(strategy, energy, bad_energy, bad_bpm) -> None:
    original = recommend_playlist([_track(p, energy) for p in ("a", "b", "c")], strategy, DJControls(start_path="a"))
    result = recommendation_with_replacement(original, "b", [_track("bad", bad_energy, bpm=bad_bpm)])
    assert [t.path for t in result.ordered_tracks] == [t.path for t in original.ordered_tracks if t.path != "b"]


@pytest.mark.parametrize(
    "strategy,controls",
    [
        ("harmonic_journey", DJControls(genre=" House ")),
        ("same_genre", DJControls(start_path="a")),
    ],
)
def test_direct_backfill_retains_active_genre(strategy, controls) -> None:
    original = recommend_playlist([_track(p) for p in ("a", "b", "c")], strategy, controls)
    result = recommendation_with_replacement(original, "b", [_track("bad", genre="Rock")])
    assert {t.path for t in result.ordered_tracks} == {"a", "c"}


@pytest.mark.parametrize(
    "strategy,controls",
    [
        ("harmonic_journey", DJControls(genre="absent")),
        ("same_genre", DJControls(start_path="a")),
    ],
)
def test_backfill_keeps_documented_genre_fallback(strategy, controls) -> None:
    original = recommend_playlist([_track("a"), _track("b", genre="Rock")], strategy, controls)
    result = recommendation_with_replacement(original, "b", [_track("replacement", genre="Jazz")])
    assert {t.path for t in result.ordered_tracks} == {"a", "replacement"}


@pytest.mark.parametrize("controls", [DJControls(), DJControls(start_path="a"), DJControls(manual_order_paths=["a"])])
def test_energy_anchor_survives_removal_reordering_and_serialization(controls) -> None:
    original = recommend_playlist([_track("a"), _track("b", 6), _track("c", 6)], "same_energy", controls)
    original = recommendation_without_paths(original, frozenset({"a"}))
    original = recommendation_reordered(original, ["c", "b"])
    original = PlaylistRecommendation.model_validate_json(original.model_dump_json())
    result = recommendation_with_replacement(original, "b", [_track("bad", 7)])
    assert [t.path for t in result.ordered_tracks] == ["c"]
    result = recommendation_with_replacement(original, "b", [_track("good", 4)])
    assert [t.path for t in result.ordered_tracks] == ["c", "good"]


@pytest.mark.parametrize(
    "strategy,bad",
    [
        ("same_color", _color("bad", 0.5)),
        ("same_color_energy", _color("bad", energy=6)),
    ],
)
def test_color_anchor_binding_survives_removal(strategy, bad) -> None:
    original = recommend_playlist(
        [_color("a", 0.5), _color("b"), _color("c")], strategy, DJControls(locked_paths={"a"}), color_anchor_path="b"
    )
    original = recommendation_without_paths(original, frozenset({"b"}))
    original = PlaylistRecommendation.model_validate_json(original.model_dump_json())
    result = recommendation_with_replacement(original, "c", [bad])
    assert [t.path for t in result.ordered_tracks] == ["a"]
    result = recommendation_with_replacement(original, "c", [_color("good")])
    assert {t.path for t in result.ordered_tracks} == {"a", "good"}


def test_backfill_keeps_custom_loudness_band_and_unmeasured_exception() -> None:
    original = recommend_playlist(
        [_loud("a", -18), _loud("b", -18)], "consistent_loudness", loudness_band=LoudnessBand(-18, 1)
    )
    assert len(recommendation_with_replacement(original, "b", [_loud("bad", -10)]).ordered_tracks) == 1
    for good in (_loud("boundary", -19), _track("unmeasured")):
        assert good in recommendation_with_replacement(original, "b", [good]).ordered_tracks


@pytest.mark.parametrize("strategy", ["same_energy", "same_genre", "same_color", "consistent_loudness"])
def test_legacy_missing_policy_does_not_invent_context(strategy) -> None:
    original = recommend_playlist([_color("a"), _color("b")], strategy)
    original = PlaylistRecommendation.model_validate(original.model_dump(exclude={"replacement_policy"}))
    result = recommendation_with_replacement(original, "b", [_color("candidate")])
    assert [t.path for t in result.ordered_tracks] == ["a"]
    assert any("context unavailable" in warning for warning in result.warnings)


@pytest.mark.parametrize("exclude", [False, True])
@pytest.mark.parametrize(
    "strategy", ["same_energy", "same_color", "same_color_energy", "harmonic_journey", "consistent_loudness"]
)
def test_current_lock_exception_is_additive_and_exclusions_win(exclude: bool, strategy: str) -> None:
    original = recommend_playlist([_color("a"), _color("b")], strategy, DJControls(genre="House"))
    result = recommendation_with_replacement(
        original,
        "b",
        [_loud("locked", -30).model_copy(update={"energy_level": 10, "genre": "Rock"})],
        locked_paths=frozenset({"locked"}),
        excluded_paths=frozenset({"locked"}) if exclude else frozenset(),
    )
    assert {t.path for t in result.ordered_tracks} == ({"a"} if exclude else {"a", "locked"})


def test_missing_color_anchor_stays_closed_but_missing_energy_keeps_existing_fallback() -> None:
    for strategy, candidate, expected in (
        ("same_color", _color("candidate"), {"a"}),
        ("same_energy", _track("candidate", 10), {"a", "candidate"}),
    ):
        tracks = [_track(p).model_copy(update={"energy_level": None}) for p in ("a", "b")]
        original = recommend_playlist(tracks, strategy, DJControls(manual_order_paths=["a", "b"]))
        result = recommendation_with_replacement(original, "b", [candidate])
        assert {t.path for t in result.ordered_tracks} == expected


def test_replacement_keeps_input_tie_order_after_filtering() -> None:
    original = recommend_playlist([_track("a"), _track("b")], "build")
    # Equal energy distance/transition score: existing helper chooses first input.
    first, second = _track("z", 6), _track("y", 4)
    result = recommendation_with_replacement(original, "b", [first, second])
    assert first in result.ordered_tracks


@pytest.mark.parametrize("legacy", [False, True])
def test_explicit_loudness_override_filters_backfill_without_rebinding_anchors(legacy: bool) -> None:
    original = recommend_playlist(
        [_loud("a", -18), _loud("b", -18)], "consistent_loudness", loudness_band=LoudnessBand(-18, 1)
    )
    if legacy:
        original = original.model_copy(update={"replacement_policy": None})
    result = recommendation_with_replacement(
        original,
        "b",
        [_loud("old-band", -18), _loud("default-band", -10), _loud("new-band", -14)],
        loudness_band=LoudnessBand(-14, 0.5),
    )
    assert [track.path for track in result.ordered_tracks] == ["a", "new-band"]
    if not legacy:
        assert original.replacement_policy is not None
        assert original.replacement_policy.loudness_band == LoudnessBand(-18, 1)
        assert result.replacement_policy is not None
        assert result.replacement_policy.loudness_band == LoudnessBand(-14, 0.5)
