from unittest.mock import patch

import pytest

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import (
    COLOR_CENTROID_REL_MAX,
    COLOR_RGB_L1_MAX,
    COLOR_ROLLOFF_REL_MAX,
    PlaylistRecommendation,
    _apply_color_filter,
    _apply_energy_tolerance,
    _bpm_jump_warning,
    _drop_generated_tracks_after_impossible_bpm_jumps,
    _same_color_energy_eligible,
    _spectral_jump_warnings,
    prefilter_strategy_candidates,
    recommend_playlist,
    recommendation_with_replacement,
    recommendation_without_paths,
)
from xfinaudio.recommendation.scoring import ScoringWeights, score_transition
from xfinaudio.recommendation.strategies import StrategyRegistry, get_strategy


def track(
    path: str,
    *,
    bpm: float | None = 120.0,
    camelot_key: str | None = "8A",
    energy_level: int | None = 5,
    genre: str | None = "House",
    tags: list[str] | None = None,
    status: str = "complete",
    duration: float | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path.rsplit("/", maxsplit=1)[-1],
        duration=duration,
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        genre=genre,
        tags=["Peak"] if tags is None else tags,
        metadata_status=status,  # type: ignore[arg-type]
    )


def spectral_track(path: str, color: ColorName) -> TrackRecord:
    # Finite positive centroid/rolloff so same-label candidates share the gate's
    # relative-delta denominators (delta 0) and pass the bounded proximity gate,
    # which since tighten-spectral-color-filters spans every dominant-color label.
    # `same_color` (label-only via `_apply_color_filter`) is unaffected by these.
    return track(path).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=1.0 if color == "RED" else 0.0,
                green_ratio=1.0 if color == "GREEN" else 0.0,
                blue_ratio=1.0 if color == "BLUE" else 0.0,
                centroid_hz=1000.0,
                rolloff_hz=2000.0,
                dominant_color=color,
            )
        }
    )


def test_recommendation_without_paths_recomputes_new_middle_seam() -> None:
    recommendation = recommend_playlist(
        [
            track("/left.flac", bpm=120.0, camelot_key="8A", energy_level=4),
            track("/middle.flac", bpm=121.0, camelot_key="9A", energy_level=5),
            track("/right.flac", bpm=122.0, camelot_key="10A", energy_level=6),
        ],
        "build",
    )

    result = recommendation_without_paths(recommendation, frozenset({"/middle.flac"}))

    assert [item.path for item in result.ordered_tracks] == ["/left.flac", "/right.flac"]
    assert len(result.transition_scores) == 1
    assert result.transition_scores[0].left_path == "/left.flac"
    assert result.transition_scores[0].right_path == "/right.flac"
    assert result.total_score == result.transition_scores[0].total_score


def test_recommendation_without_paths_preserves_spectral_cohesion_for_new_seam() -> None:
    recommendation = recommend_playlist(
        [
            spectral_track("/left.flac", "RED"),
            spectral_track("/middle.flac", "GREEN"),
            spectral_track("/right.flac", "RED").model_copy(update={"energy_level": 7}),
        ],
        "build",
        spectral_cohesion=1.0,
    )
    removed_paths = frozenset({"/middle.flac"})

    without_cohesion = recommendation_without_paths(recommendation, removed_paths, spectral_cohesion=0.0)
    with_cohesion = recommendation_without_paths(recommendation, removed_paths, spectral_cohesion=1.0)

    assert with_cohesion.transition_scores[0].component_scores["spectral"] > 0.0
    assert with_cohesion.transition_scores[0].total_score != without_cohesion.transition_scores[0].total_score


def test_recommendation_without_paths_returns_unchanged_when_nothing_matches() -> None:
    recommendation = recommend_playlist([track("/a.flac"), track("/b.flac")], "build")

    assert recommendation_without_paths(recommendation, frozenset()) is recommendation
    assert recommendation_without_paths(recommendation, frozenset({"/missing.flac"})) is recommendation


def test_recommendation_without_paths_removes_first_and_last_tracks() -> None:
    recommendation = recommend_playlist(
        [track("/first.flac"), track("/middle.flac"), track("/last.flac")],
        "build",
    )

    result = recommendation_without_paths(recommendation, frozenset({"/first.flac", "/last.flac"}))

    assert [item.path for item in result.ordered_tracks] == ["/middle.flac"]
    assert result.transition_scores == []
    assert result.total_score == 0.0


def test_recommendation_without_paths_handles_all_tracks_removed() -> None:
    recommendation = recommend_playlist([track("/a.flac"), track("/b.flac")], "build")

    result = recommendation_without_paths(recommendation, frozenset({"/a.flac", "/b.flac"}))

    assert result.ordered_tracks == []
    assert result.transition_scores == []
    assert result.total_score == 0.0


def test_recommend_playlist_excludes_incomplete_tracks() -> None:
    tracks = [track("/complete.flac"), track("/incomplete.flac", status="incomplete")]

    result = recommend_playlist(tracks, "harmonic_journey")

    assert [item.path for item in result.ordered_tracks] == ["/complete.flac"]
    assert "Excluded 1 incomplete track(s)" in result.warnings


def test_recommend_playlist_applies_warmup_strategy_filtering_and_order_hints() -> None:
    tracks = [
        track("/high.flac", energy_level=9),
        track("/z-low.flac", energy_level=2),
        track("/a-mid.flac", energy_level=5),
    ]

    result = recommend_playlist(tracks, "warmup")

    assert [item.path for item in result.ordered_tracks] == ["/z-low.flac", "/a-mid.flac"]
    assert "Filtered 1 track(s) outside warmup energy range" in result.warnings


def test_recommend_playlist_respects_excluded_start_and_end_controls() -> None:
    tracks = [track("/a.flac"), track("/b.flac", camelot_key="9A"), track("/c.flac")]
    controls = DJControls(excluded_paths={"/b.flac"}, start_path="/c.flac", end_path="/a.flac")

    result = recommend_playlist(tracks, "harmonic_journey", controls=controls)

    assert [item.path for item in result.ordered_tracks] == ["/c.flac", "/a.flac"]
    assert result.applied_controls["excluded_paths"] == ["/b.flac"]


def test_recommend_playlist_preserves_locked_tracks_filtered_out_by_strategy() -> None:
    tracks = [track("/low.flac", energy_level=3), track("/locked-high.flac", energy_level=9)]
    controls = DJControls(locked_paths={"/locked-high.flac"})

    result = recommend_playlist(tracks, "warmup", controls=controls)

    assert sorted(item.path for item in result.ordered_tracks) == ["/locked-high.flac", "/low.flac"]
    assert result.applied_controls["locked_paths"] == ["/locked-high.flac"]


def test_recommend_playlist_preserves_manual_order_prefix_where_feasible() -> None:
    tracks = [track("/a.flac"), track("/b.flac"), track("/c.flac")]
    controls = DJControls(manual_order_paths=["/c.flac", "/a.flac"])

    result = recommend_playlist(tracks, "harmonic_journey", controls=controls)

    assert [item.path for item in result.ordered_tracks[:2]] == ["/c.flac", "/a.flac"]
    assert sorted(item.path for item in result.ordered_tracks) == ["/a.flac", "/b.flac", "/c.flac"]


def test_recommend_playlist_allows_end_path_inside_manual_order_without_crashing() -> None:
    tracks = [track("/a.flac"), track("/b.flac"), track("/c.flac")]
    controls = DJControls(manual_order_paths=["/c.flac", "/a.flac"], end_path="/c.flac")

    result = recommend_playlist(tracks, "harmonic_journey", controls=controls)

    assert result.ordered_tracks[-1].path == "/c.flac"
    assert sorted(item.path for item in result.ordered_tracks) == ["/a.flac", "/b.flac", "/c.flac"]


def test_recommend_playlist_uses_custom_weights_override() -> None:
    left = track("/left.flac", bpm=120.0, energy_level=5, tags=["A"])
    same_bpm = track("/same-bpm.flac", bpm=120.0, energy_level=9, tags=["B"])
    same_energy = track("/same-energy.flac", bpm=135.0, energy_level=5, tags=["B"])

    result = recommend_playlist(
        [same_energy, left, same_bpm],
        "harmonic_journey",
        controls=DJControls(start_path="/left.flac"),
        weights_override=ScoringWeights(harmonic=0.0, bpm=1.0, energy=0.0, tags=0.0),
    )

    assert [item.path for item in result.ordered_tracks[:2]] == ["/left.flac", "/same-bpm.flac"]


def test_recommend_playlist_same_vibe_degrades_gracefully_when_tags_are_unavailable() -> None:
    tracks = [
        track("/a.flac", genre=None, tags=[]),
        track("/b.flac", genre=None, tags=[]),
    ]

    result = recommend_playlist(tracks, "same_vibe")

    assert isinstance(result, PlaylistRecommendation)
    assert [item.path for item in result.ordered_tracks] == ["/a.flac", "/b.flac"]
    assert "same_vibe metadata unavailable; falling back to harmonic sequencing" in result.warnings


def test_same_genre_filters_candidates_to_selected_start_genre() -> None:
    tracks = [
        track("/anchor.flac", genre=" World & Latin ", tags=["World & Latin"]),
        track("/latin-a.flac", genre="world & latin", tags=["World & Latin"]),
        track("/rock.flac", genre="Rock", tags=["Rock"]),
        track("/latin-b.flac", genre="WORLD & LATIN", tags=["World & Latin"]),
    ]

    result = recommend_playlist(tracks, "same_genre", controls=DJControls(start_path="/anchor.flac"))

    assert {item.path for item in result.ordered_tracks} == {"/anchor.flac", "/latin-a.flac", "/latin-b.flac"}
    assert "same_genre filter applied: world & latin" in result.warnings


def test_same_genre_uses_manual_prefix_genre_when_start_path_is_absent() -> None:
    tracks = [
        track("/manual.flac", genre="Disco", tags=["Disco"]),
        track("/disco.flac", genre="disco", tags=["Disco"]),
        track("/house.flac", genre="House", tags=["House"]),
    ]

    result = recommend_playlist(tracks, "same_genre", controls=DJControls(manual_order_paths=["/manual.flac"]))

    assert [item.path for item in result.ordered_tracks[:1]] == ["/manual.flac"]
    assert {item.path for item in result.ordered_tracks} == {"/manual.flac", "/disco.flac"}
    assert "same_genre filter applied: disco" in result.warnings


def test_same_genre_preserves_controlled_paths_even_when_genre_differs() -> None:
    tracks = [
        track("/anchor.flac", genre="House", tags=["House"]),
        track("/house.flac", genre="House", tags=["House"]),
        track("/locked-rock.flac", genre="Rock", tags=["Rock"]),
        track("/end-pop.flac", genre="Pop", tags=["Pop"]),
    ]
    controls = DJControls(start_path="/anchor.flac", end_path="/end-pop.flac", locked_paths={"/locked-rock.flac"})

    result = recommend_playlist(tracks, "same_genre", controls=controls)

    assert {item.path for item in result.ordered_tracks} == {
        "/anchor.flac",
        "/house.flac",
        "/locked-rock.flac",
        "/end-pop.flac",
    }
    assert "same_genre filter applied: house" in result.warnings


def test_same_genre_falls_back_when_no_eligible_candidate_matches_anchor_genre() -> None:
    tracks = [
        track("/anchor.flac", genre="World & Latin", tags=["World & Latin"]),
        track("/rock.flac", genre="Rock", tags=["Rock"]),
        track("/house.flac", genre="House", tags=["House"]),
    ]

    result = recommend_playlist(tracks, "same_genre", controls=DJControls(start_path="/anchor.flac"))

    assert {item.path for item in result.ordered_tracks} == {"/anchor.flac", "/rock.flac", "/house.flac"}
    assert "same_genre filter applied: world & latin" in result.warnings
    assert (
        "same_genre: no candidates match anchor genre 'world & latin'; falling back to unfiltered scoring"
        in result.warnings
    )


def test_same_color_filters_candidates_to_selected_start_color() -> None:
    tracks = [
        spectral_track("/anchor.flac", "RED"),
        spectral_track("/red.flac", "RED"),
        spectral_track("/green.flac", "GREEN"),
        track("/no-profile.flac"),
        spectral_track("/blue.flac", "BLUE"),
    ]

    result = recommend_playlist(tracks, "same_color", controls=DJControls(start_path="/anchor.flac"))

    assert {item.path for item in result.ordered_tracks} == {"/anchor.flac", "/red.flac"}
    assert "same_color filter applied: RED" in result.warnings


def test_same_color_uses_manual_prefix_color_when_start_path_is_absent() -> None:
    tracks = [
        spectral_track("/manual.flac", "GREEN"),
        spectral_track("/green.flac", "GREEN"),
        spectral_track("/red.flac", "RED"),
    ]

    result = recommend_playlist(tracks, "same_color", controls=DJControls(manual_order_paths=["/manual.flac"]))

    assert [item.path for item in result.ordered_tracks[:1]] == ["/manual.flac"]
    assert {item.path for item in result.ordered_tracks} == {"/manual.flac", "/green.flac"}
    assert "same_color filter applied: GREEN" in result.warnings


def test_same_color_preserves_controlled_paths_even_when_color_differs() -> None:
    tracks = [
        spectral_track("/anchor.flac", "RED"),
        spectral_track("/red.flac", "RED"),
        spectral_track("/locked-green.flac", "GREEN"),
        spectral_track("/end-blue.flac", "BLUE"),
    ]
    controls = DJControls(start_path="/anchor.flac", end_path="/end-blue.flac", locked_paths={"/locked-green.flac"})

    result = recommend_playlist(tracks, "same_color", controls=controls)

    assert {item.path for item in result.ordered_tracks} == {
        "/anchor.flac",
        "/red.flac",
        "/locked-green.flac",
        "/end-blue.flac",
    }
    assert "same_color filter applied: RED" in result.warnings


def test_same_color_falls_back_when_no_eligible_candidate_matches_anchor_color() -> None:
    tracks = [
        spectral_track("/anchor.flac", "RED"),
        spectral_track("/green.flac", "GREEN"),
        spectral_track("/blue.flac", "BLUE"),
    ]

    result = recommend_playlist(tracks, "same_color", controls=DJControls(start_path="/anchor.flac"))

    assert {item.path for item in result.ordered_tracks} == {"/anchor.flac", "/green.flac", "/blue.flac"}
    assert "same_color filter applied: RED" in result.warnings
    assert "same_color: no candidates match anchor color 'RED'; falling back to unfiltered scoring" in result.warnings


def test_same_color_skips_filter_when_no_track_has_a_profile() -> None:
    tracks = [track("/a.flac"), track("/b.flac")]

    result = recommend_playlist(tracks, "same_color")

    assert {item.path for item in result.ordered_tracks} == {"/a.flac", "/b.flac"}
    assert not any(warning.startswith("same_color") for warning in result.warnings)


def test_same_color_output_and_warnings_are_stable_after_seam_widening() -> None:
    """Characterization baseline (Task 1): freeze same_color output/warnings before dispatch is widened."""
    tracks = [
        spectral_track("/anchor.flac", "RED"),
        spectral_track("/red-a.flac", "RED"),
        spectral_track("/red-b.flac", "RED"),
        spectral_track("/green.flac", "GREEN"),
        track("/no-profile.flac"),
        spectral_track("/blue.flac", "BLUE"),
    ]

    result = recommend_playlist(tracks, "same_color", controls=DJControls(start_path="/anchor.flac"))

    assert [item.path for item in result.ordered_tracks] == ["/anchor.flac", "/red-a.flac", "/red-b.flac"]
    assert result.warnings == ["same_color filter applied: RED"]


def test_same_energy_output_and_warnings_are_stable_after_seam_widening() -> None:
    """Characterization baseline (Task 1): freeze same_energy output/warnings before dispatch is widened."""
    tracks = [
        track("/anchor.flac", energy_level=5),
        track("/near_low.flac", energy_level=4),
        track("/near_same.flac", energy_level=5),
        track("/near_high.flac", energy_level=6),
        track("/too_low.flac", energy_level=1),
        track("/too_high.flac", energy_level=9),
    ]

    result = recommend_playlist(tracks, "same_energy", controls=DJControls(start_path="/anchor.flac"))

    assert [item.path for item in result.ordered_tracks] == [
        "/anchor.flac",
        "/near_high.flac",
        "/near_same.flac",
        "/near_low.flac",
    ]
    assert result.warnings == ["Filtered 2 track(s) outside same_energy energy tolerance"]


def test_same_color_energy_filters_candidates_to_anchor_color() -> None:
    tracks = [
        spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/red-near.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/green.flac", "GREEN").model_copy(update={"energy_level": 5}),
        spectral_track("/blue.flac", "BLUE").model_copy(update={"energy_level": 5}),
    ]

    result = recommend_playlist(tracks, "same_color_energy", controls=DJControls(start_path="/anchor.flac"))

    non_control = [item for item in result.ordered_tracks if item.path != "/anchor.flac"]
    assert non_control
    for candidate in non_control:
        profile = candidate.spectral_profile
        assert profile is not None
        assert profile.dominant_color == "RED"


def test_same_color_energy_enforces_exact_anchor_energy() -> None:
    # Behavior changed by tighten-same-color-energy: same_color_energy now requires
    # EXACT anchor energy for generated candidates, not the old anchor +/-1 band.
    # The E4 (near_low) and E6 (near_high) neighbours that the +/-1 band admitted
    # are now excluded; only the E5 match survives alongside the anchor.
    tracks = [
        spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/near_low.flac", "RED").model_copy(update={"energy_level": 4}),
        spectral_track("/near_same.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/near_high.flac", "RED").model_copy(update={"energy_level": 6}),
        spectral_track("/too_low.flac", "RED").model_copy(update={"energy_level": 1}),
        spectral_track("/too_high.flac", "RED").model_copy(update={"energy_level": 9}),
    ]

    result = recommend_playlist(tracks, "same_color_energy", controls=DJControls(start_path="/anchor.flac"))

    paths = {item.path for item in result.ordered_tracks}
    # Anchor (control) plus the only exact-energy RED match remain.
    assert paths == {"/anchor.flac", "/near_same.flac"}
    # The old +/-1 band neighbours are now excluded.
    assert "/near_low.flac" not in paths
    assert "/near_high.flac" not in paths
    assert "/too_low.flac" not in paths
    assert "/too_high.flac" not in paths


def test_same_color_energy_composes_color_and_exact_energy_simultaneously() -> None:
    # Behavior changed by tighten-same-color-energy: a candidate must match BOTH
    # the anchor color AND the anchor's EXACT energy. Under the old +/-1 band a
    # RED E6 candidate (/near_energy) counted as "both"; now only RED E5 does.
    tracks = [
        spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/color-only.flac", "RED").model_copy(update={"energy_level": 9}),
        spectral_track("/energy-only.flac", "GREEN").model_copy(update={"energy_level": 5}),
        spectral_track("/near_energy.flac", "RED").model_copy(update={"energy_level": 6}),
        spectral_track("/both.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/neither.flac", "GREEN").model_copy(update={"energy_level": 9}),
    ]

    result = recommend_playlist(tracks, "same_color_energy", controls=DJControls(start_path="/anchor.flac"))

    paths = {item.path for item in result.ordered_tracks}
    assert paths == {"/anchor.flac", "/both.flac"}


def test_same_color_energy_preserves_control_paths() -> None:
    tracks = [
        spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/red.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/locked-green.flac", "GREEN").model_copy(update={"energy_level": 9}),
        spectral_track("/end-blue.flac", "BLUE").model_copy(update={"energy_level": 1}),
    ]
    controls = DJControls(start_path="/anchor.flac", end_path="/end-blue.flac", locked_paths={"/locked-green.flac"})

    result = recommend_playlist(tracks, "same_color_energy", controls=controls)

    assert {item.path for item in result.ordered_tracks} == {
        "/anchor.flac",
        "/red.flac",
        "/locked-green.flac",
        "/end-blue.flac",
    }


def test_same_color_energy_empty_strict_pool_fails_closed_without_widening() -> None:
    # Behavior changed by tighten-same-color-energy: an empty strict pool no longer
    # widens to unfiltered scoring. Only preserved controls survive, and a
    # strict-constraint warning is emitted instead of the old fallback warning.
    tracks = [
        spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/green.flac", "GREEN").model_copy(update={"energy_level": 5}),
        spectral_track("/blue.flac", "BLUE").model_copy(update={"energy_level": 6}),
    ]

    result = recommend_playlist(tracks, "same_color_energy", controls=DJControls(start_path="/anchor.flac"))

    # The non-matching candidates are NOT reintroduced; only the anchor control remains.
    assert {item.path for item in result.ordered_tracks} == {"/anchor.flac"}
    # No widening: the old unfiltered-fallback warning must never appear.
    assert not any("falling back to unfiltered scoring" in warning for warning in result.warnings)
    assert any("same_color_energy" in warning and "strict" in warning.lower() for warning in result.warnings)


def test_prefilter_strategy_candidates_applies_color_and_exact_energy_for_same_color_energy() -> None:
    # Behavior changed by tighten-same-color-energy: the prefilter now enforces
    # EXACT anchor energy for same_color_energy (no +/-1 band). A RED E6 candidate
    # that the old band admitted is now excluded; only the RED E5 match survives.
    anchor = spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5})
    near_energy = spectral_track("/near_energy.flac", "RED").model_copy(update={"energy_level": 6})
    both = spectral_track("/both.flac", "RED").model_copy(update={"energy_level": 5})
    color_only = spectral_track("/color-only.flac", "RED").model_copy(update={"energy_level": 9})
    energy_only = spectral_track("/energy-only.flac", "GREEN").model_copy(update={"energy_level": 5})

    result = prefilter_strategy_candidates(
        [anchor, near_energy, both, color_only, energy_only],
        "same_color_energy",
        controls=DJControls(start_path="/anchor.flac"),
    )

    assert {item.path for item in result} == {"/anchor.flac", "/both.flac"}


def test_prefilter_strategy_candidates_keeps_only_anchor_color_for_same_color() -> None:
    reds = [spectral_track(f"/red-{i}.flac", "RED") for i in range(30)]
    greens = [spectral_track(f"/green-{i}.flac", "GREEN") for i in range(30)]

    result = prefilter_strategy_candidates(
        [*reds, *greens], "same_color", controls=DJControls(start_path="/green-0.flac")
    )

    assert {item.path for item in result} == {green.path for green in greens}


def test_prefilter_strategy_candidates_applies_energy_range_for_peak_time() -> None:
    low = track("/low.flac", energy_level=3)
    high = track("/high.flac", energy_level=8)

    result = prefilter_strategy_candidates([low, high], "peak_time")

    assert [item.path for item in result] == ["/high.flac"]


def test_prefilter_strategy_candidates_applies_energy_tolerance_for_same_energy() -> None:
    anchor = track("/anchor.flac", energy_level=5)
    near = track("/near.flac", energy_level=6)
    far = track("/far.flac", energy_level=9)

    result = prefilter_strategy_candidates(
        [anchor, near, far], "same_energy", controls=DJControls(start_path="/anchor.flac")
    )

    assert {item.path for item in result} == {"/anchor.flac", "/near.flac"}


def _three_track_recommendation() -> PlaylistRecommendation:
    return recommend_playlist(
        [
            track("/left.flac", bpm=120.0, camelot_key="8A", energy_level=4),
            track("/removed.flac", bpm=121.0, camelot_key="9A", energy_level=5),
            track("/right.flac", bpm=122.0, camelot_key="10A", energy_level=6),
        ],
        "build",
    )


def test_recommendation_with_replacement_fills_the_slot_with_best_fitting_candidate() -> None:
    recommendation = _three_track_recommendation()
    good_fit = track("/good.flac", bpm=121.0, camelot_key="9A", energy_level=5)
    bad_fit = track("/bad.flac", bpm=90.0, camelot_key="2B", energy_level=1)

    result = recommendation_with_replacement(recommendation, "/removed.flac", [bad_fit, good_fit])

    assert [item.path for item in result.ordered_tracks] == ["/left.flac", "/good.flac", "/right.flac"]
    assert len(result.transition_scores) == 2
    assert result.transition_scores[0].right_path == "/good.flac"
    assert result.transition_scores[1].left_path == "/good.flac"
    assert result.total_score == sum(score.total_score for score in result.transition_scores)


def test_recommendation_with_replacement_ignores_candidates_already_in_playlist() -> None:
    recommendation = _three_track_recommendation()
    duplicate = track("/right.flac", bpm=122.0, camelot_key="10A", energy_level=6)

    result = recommendation_with_replacement(recommendation, "/removed.flac", [duplicate])

    assert [item.path for item in result.ordered_tracks] == ["/left.flac", "/right.flac"]


def test_recommendation_with_replacement_shrinks_when_no_candidate_is_eligible() -> None:
    recommendation = _three_track_recommendation()

    result = recommendation_with_replacement(recommendation, "/removed.flac", [])

    assert [item.path for item in result.ordered_tracks] == ["/left.flac", "/right.flac"]
    assert len(result.transition_scores) == 1


def test_recommendation_with_replacement_returns_same_object_for_unknown_path() -> None:
    recommendation = _three_track_recommendation()

    result = recommendation_with_replacement(recommendation, "/absent.flac", [track("/candidate.flac")])

    assert result is recommendation


def test_recommendation_with_replacement_handles_edge_slots() -> None:
    recommendation = _three_track_recommendation()
    candidate = track("/new-start.flac", bpm=119.0, camelot_key="7A", energy_level=4)

    result = recommendation_with_replacement(recommendation, "/left.flac", [candidate])

    assert [item.path for item in result.ordered_tracks] == ["/new-start.flac", "/removed.flac", "/right.flac"]


def test_prefilter_strategy_candidates_passes_through_unconstrained_strategies() -> None:
    tracks = [track("/a.flac"), track("/b.flac", status="incomplete")]

    result = prefilter_strategy_candidates(tracks, "harmonic_journey")

    assert [item.path for item in result] == ["/a.flac"]


def test_recommend_playlist_uses_injected_strategy_registry() -> None:
    peak_as_custom = get_strategy("peak_time").model_copy(update={"name": "custom_peak"})
    registry = StrategyRegistry([peak_as_custom])
    tracks = [track("/low.flac", energy_level=3), track("/high.flac", energy_level=9)]

    result = recommend_playlist(tracks, "custom_peak", strategy_registry=registry)

    assert result.strategy.name == "custom_peak"
    assert [item.path for item in result.ordered_tracks] == ["/high.flac"]


def test_warmup_drops_generated_tracks_after_impossible_bpm_jump_from_selected_start() -> None:
    tracks = [
        track("/stay.flac", bpm=102.34, camelot_key="4A", energy_level=7, genre="Disco", tags=["Disco"]),
        track("/thinking.flac", bpm=104.14, camelot_key="3A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/more.flac", bpm=106.09, camelot_key="9A", energy_level=6, genre="Disco", tags=["Disco"]),
        track("/knock.flac", bpm=122.0, camelot_key="11B", energy_level=6, genre="Disco", tags=["Disco"]),
        track("/number.flac", bpm=121.87, camelot_key="11A", energy_level=6, genre="Disco", tags=["Disco"]),
    ]

    result = recommend_playlist(tracks, "warmup", controls=DJControls(start_path="/stay.flac"))

    assert [item.path for item in result.ordered_tracks] == ["/stay.flac", "/thinking.flac", "/more.flac"]
    assert all(score.component_scores["bpm"] > 0.0 for score in result.transition_scores)
    assert "Dropped 2 generated track(s) because adjacent BPM jump exceeded 3.0%" in result.warnings


def test_harmonic_journey_drops_generated_tracks_after_bpm_jump_over_three_percent() -> None:
    tracks = [
        track("/start.flac", bpm=100.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/good.flac", bpm=102.9, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/too-fast.flac", bpm=106.1, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
    ]

    result = recommend_playlist(tracks, "harmonic_journey", controls=DJControls(start_path="/start.flac"))

    assert [item.path for item in result.ordered_tracks] == ["/start.flac", "/good.flac"]
    assert "Dropped 1 generated track(s) because adjacent BPM jump exceeded 3.0%" in result.warnings
    assert all(score.component_scores["bpm"] > 0.0 for score in result.transition_scores)


def test_warmup_drops_generated_track_after_impossible_bpm_jump_from_manual_prefix() -> None:
    tracks = [
        track("/manual.flac", bpm=100.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/too-fast.flac", bpm=140.0, camelot_key="8A", energy_level=2, genre="Disco", tags=["Disco"]),
        track("/ok.flac", bpm=101.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
    ]

    result = recommend_playlist(tracks, "warmup", controls=DJControls(manual_order_paths=["/manual.flac"]))

    assert [item.path for item in result.ordered_tracks] == ["/manual.flac", "/ok.flac"]
    assert "Dropped 1 generated track(s) because adjacent BPM jump exceeded 3.0%" in result.warnings


def test_harmonic_journey_drops_generated_track_after_bpm_jump_from_manual_seam() -> None:
    tracks = [
        track("/manual.flac", bpm=100.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/too-fast.flac", bpm=140.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
    ]

    result = recommend_playlist(tracks, "harmonic_journey", controls=DJControls(manual_order_paths=["/manual.flac"]))

    assert [item.path for item in result.ordered_tracks] == ["/manual.flac"]
    expected_warning = _bpm_jump_warning(
        1, suffix=" while re-validating the sequence anchored on the manually ordered tracks"
    )
    assert expected_warning in result.warnings


def test_harmonic_journey_pre_and_post_sequencing_bpm_gates_drop_different_tracks() -> None:
    # harmonic_journey has no sort_hint override (defaults to alphabetical-by-path sorting
    # applied before controls are resolved), so remaining_tracks (manual excluded) is ordered
    # [a-kept-by-pregate, b-dropped-by-pregate]:
    # - the pre-sequencing gate (playlist_service.py:114, unchanged) anchors on
    #   "/a-kept-by-pregate.flac" (first remaining track) and drops
    #   "/b-dropped-by-pregate.flac" for its jump from that anchor.
    # - the surviving "/a-kept-by-pregate.flac" then reaches the new post-sequencing gate,
    #   which is seeded with the manual anchor and drops it for its jump from "/manual.flac".
    tracks = [
        track("/manual.flac", bpm=100.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/a-kept-by-pregate.flac", bpm=104.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/b-dropped-by-pregate.flac", bpm=140.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
    ]

    result = recommend_playlist(tracks, "harmonic_journey", controls=DJControls(manual_order_paths=["/manual.flac"]))

    pre_sequencing_warning = _bpm_jump_warning(1)
    post_sequencing_warning = _bpm_jump_warning(
        1, suffix=" while re-validating the sequence anchored on the manually ordered tracks"
    )
    assert pre_sequencing_warning in result.warnings
    assert post_sequencing_warning in result.warnings
    assert pre_sequencing_warning != post_sequencing_warning
    assert [item.path for item in result.ordered_tracks] == ["/manual.flac"]


def test_score_cache_is_fresh_per_recommendation_session() -> None:
    """Each recommend_playlist call starts with a fresh cache — no cross-session leakage."""
    tracks = [
        track("/a.flac", bpm=120.0, camelot_key="8A", energy_level=5),
        track("/b.flac", bpm=121.0, camelot_key="8A", energy_level=5),
        track("/c.flac", bpm=122.0, camelot_key="8A", energy_level=5),
    ]

    with patch("xfinaudio.recommendation.playlist_service.score_transition", wraps=score_transition) as spy:
        recommend_playlist(tracks, "harmonic_journey")
        first_session_calls = spy.call_count

        recommend_playlist(tracks, "harmonic_journey")
        second_session_calls = spy.call_count - first_session_calls

    # Both sessions computed the same number of transitions — cache was fresh in session 2
    assert first_session_calls == second_session_calls


def test_spectral_jump_warnings_aggregate_consecutive_same_direction_shifts() -> None:
    tracks = [
        spectral_track("/red-1.flac", "RED"),
        spectral_track("/green-1.flac", "GREEN"),
        spectral_track("/red-2.flac", "RED"),
        spectral_track("/green-2.flac", "GREEN"),
        spectral_track("/blue.flac", "BLUE"),
        spectral_track("/red-3.flac", "RED"),
    ]

    warnings = _spectral_jump_warnings(tracks)

    assert warnings == [
        "Spectral shifts: RED→GREEN (2 times), GREEN→RED (1 time), GREEN→BLUE (1 time), BLUE→RED (1 time)"
    ]


def test_spectral_jump_warnings_ignore_same_color_and_missing_profiles() -> None:
    tracks = [
        spectral_track("/red-1.flac", "RED"),
        spectral_track("/red-2.flac", "RED"),
        track("/missing.flac"),
        spectral_track("/blue.flac", "BLUE"),
    ]

    assert _spectral_jump_warnings(tracks) == []


def test_bpm_jump_gate_keeps_control_paths() -> None:
    """The pre-optimizer BPM gate must not drop the anchor.

    Every other filter in the pipeline takes preserve_paths and respects control
    tracks; this one did not. recommend_sequence then raises "Unknown
    start_path". Because the gate walks the list in order and compares against
    the last kept track, it surfaced on roughly 1 in 40 real sets.

    These BPMs are from the real failure: 97.7 keeps 100.0 (2.35%), then the
    anchor at 97.05 sits 3.04% from 100.0 and falls just past the 3% limit.
    """
    tracks = [
        track("/a.flac", bpm=97.7, camelot_key="4A"),
        track("/b.flac", bpm=100.0, camelot_key="4A"),
        track("/anchor.flac", bpm=97.05, camelot_key="4A"),
        track("/d.flac", bpm=97.3, camelot_key="4A"),
    ]

    kept, _ = _drop_generated_tracks_after_impossible_bpm_jumps(tracks, preserve_paths={"/anchor.flac"})

    assert any(candidate.path == "/anchor.flac" for candidate in kept)


def test_bpm_jump_gate_still_drops_unprotected_jumps() -> None:
    """Protecting the anchor must not turn the gate off for everything else."""
    tracks = [
        track("/a.flac", bpm=97.7, camelot_key="4A"),
        track("/far.flac", bpm=140.0, camelot_key="4A"),
    ]

    kept, dropped = _drop_generated_tracks_after_impossible_bpm_jumps(tracks, preserve_paths={"/a.flac"})

    assert [candidate.path for candidate in kept] == ["/a.flac"]
    assert dropped == 1


def test_target_count_trims_the_set_without_shrinking_the_pool() -> None:
    """Pool size and set length are different questions.

    They used to be the same number: asking for 25 candidates produced a 25-track
    set, so the optimizer had exactly as many options as slots and never actually
    selected anything. Measured on a real library, widening the pool to 50 while
    keeping a 10-track set raised the mean transition score from 0.8716 to 0.9002.
    """
    tracks = [track(f"/t{index}.flac", bpm=120.0 + index * 0.5, camelot_key="8A") for index in range(30)]

    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey", target_count=10)

    assert len(recommendation.ordered_tracks) == 10
    assert len(recommendation.transition_scores) == 9


def test_target_count_larger_than_the_pool_returns_everything() -> None:
    tracks = [track(f"/t{index}.flac", bpm=120.0 + index * 0.5, camelot_key="8A") for index in range(6)]

    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey", target_count=50)

    assert len(recommendation.ordered_tracks) == 6


def test_without_target_count_no_trimming_is_applied() -> None:
    """Existing callers keep the current behaviour.

    The untrimmed result is not necessarily the whole input -- the BPM gate can
    still drop tracks -- so this compares against a trimmed run rather than
    asserting a fixed length.
    """
    tracks = [track(f"/t{index}.flac", bpm=120.0 + index * 0.5, camelot_key="8A") for index in range(12)]

    untrimmed = recommend_playlist(tracks, strategy_name="harmonic_journey")
    trimmed = recommend_playlist(tracks, strategy_name="harmonic_journey", target_count=4)

    assert len(trimmed.ordered_tracks) == 4
    assert len(untrimmed.ordered_tracks) > 4


def test_target_count_keeps_the_anchor_first() -> None:
    tracks = [track(f"/t{index}.flac", bpm=120.0 + index * 0.5, camelot_key="8A") for index in range(20)]

    recommendation = recommend_playlist(
        tracks,
        strategy_name="harmonic_journey",
        controls=DJControls(start_path="/t7.flac"),
        target_count=5,
    )

    assert len(recommendation.ordered_tracks) == 5
    assert recommendation.ordered_tracks[0].path == "/t7.flac"


def test_target_duration_fills_the_requested_time() -> None:
    """A DJ books minutes, not track counts.

    A fixed count of 10 produced sets between 36 and 71 minutes on the real
    library, because track lengths vary. Asking for time uses the real durations
    of the tracks actually chosen.
    """
    tracks = [
        track(f"/t{index}.flac", bpm=120.0 + index * 0.4, camelot_key="8A", duration=300.0) for index in range(20)
    ]

    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey", target_duration_minutes=30.0)

    total_minutes = sum(t.duration or 0.0 for t in recommendation.ordered_tracks) / 60
    assert 25.0 <= total_minutes <= 35.0
    assert len(recommendation.ordered_tracks) == 6


def test_target_duration_adapts_to_longer_tracks() -> None:
    """The same 30 minutes is fewer tracks when the tracks run long."""
    long_tracks = [
        track(f"/t{index}.flac", bpm=120.0 + index * 0.4, camelot_key="8A", duration=600.0) for index in range(20)
    ]

    recommendation = recommend_playlist(long_tracks, strategy_name="harmonic_journey", target_duration_minutes=30.0)

    assert len(recommendation.ordered_tracks) == 3


def test_target_duration_keeps_the_anchor_first() -> None:
    tracks = [
        track(f"/t{index}.flac", bpm=120.0 + index * 0.4, camelot_key="8A", duration=300.0) for index in range(20)
    ]

    recommendation = recommend_playlist(
        tracks,
        strategy_name="harmonic_journey",
        controls=DJControls(start_path="/t9.flac"),
        target_duration_minutes=15.0,
    )

    assert recommendation.ordered_tracks[0].path == "/t9.flac"
    assert len(recommendation.ordered_tracks) == 3


def test_target_duration_returns_everything_when_the_pool_is_too_short() -> None:
    tracks = [track(f"/t{index}.flac", bpm=120.0 + index * 0.4, camelot_key="8A", duration=300.0) for index in range(3)]

    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey", target_duration_minutes=120.0)

    assert len(recommendation.ordered_tracks) == 3


def test_slot_accounts_for_playing_only_a_segment_of_each_track() -> None:
    """A DJ plays a segment, not the whole track.

    Summing full durations answers "how long is this music", not "how long is my
    set". At a 4.8 minute median, a 30-minute slot is 6 tracks played whole but
    15 played two minutes at a time.
    """
    tracks = [
        track(f"/t{index}.flac", bpm=120.0 + index * 0.2, camelot_key="8A", duration=300.0) for index in range(30)
    ]

    recommendation = recommend_playlist(
        tracks,
        strategy_name="harmonic_journey",
        target_duration_minutes=30.0,
        played_seconds_per_track=120.0,
    )

    assert len(recommendation.ordered_tracks) == 15


def test_a_track_shorter_than_the_segment_only_contributes_its_length() -> None:
    """You cannot play two minutes of a ninety-second edit."""
    tracks = [track(f"/t{index}.flac", bpm=120.0 + index * 0.2, camelot_key="8A", duration=90.0) for index in range(30)]

    recommendation = recommend_playlist(
        tracks,
        strategy_name="harmonic_journey",
        target_duration_minutes=15.0,
        played_seconds_per_track=120.0,
    )

    assert len(recommendation.ordered_tracks) == 10


def test_without_a_segment_length_the_whole_track_counts() -> None:
    """Existing callers keep counting full durations."""
    tracks = [
        track(f"/t{index}.flac", bpm=120.0 + index * 0.2, camelot_key="8A", duration=300.0) for index in range(30)
    ]

    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey", target_duration_minutes=30.0)

    assert len(recommendation.ordered_tracks) == 6


# ---------------------------------------------------------------------------
# recommendation_reordered — the DJ moves a track by hand on the Export screen.
#
# The order the DJ leaves behind is what gets written to the crate, so the
# adjacency scores have to describe THAT order. Carrying the optimizer's
# original scores forward would show the Review screen seams that no longer
# exist.
# ---------------------------------------------------------------------------


def test_recommendation_reordered_rescores_the_seams_it_creates() -> None:
    from xfinaudio.recommendation.playlist_service import recommendation_reordered

    recommendation = recommend_playlist(
        [
            track("/a.flac", bpm=120.0, camelot_key="8A", energy_level=4),
            track("/b.flac", bpm=121.0, camelot_key="9A", energy_level=5),
            track("/c.flac", bpm=122.0, camelot_key="10A", energy_level=6),
        ],
        "build",
    )
    original = [item.path for item in recommendation.ordered_tracks]
    reversed_order = list(reversed(original))

    result = recommendation_reordered(recommendation, reversed_order)

    assert [item.path for item in result.ordered_tracks] == reversed_order
    assert len(result.transition_scores) == len(original) - 1
    assert result.transition_scores[0].left_path == reversed_order[0]
    assert result.transition_scores[0].right_path == reversed_order[1]
    assert result.total_score == sum(score.total_score for score in result.transition_scores)


def test_recommendation_reordered_keeps_every_track() -> None:
    """Reordering never drops anything -- removal is a separate operation."""
    from xfinaudio.recommendation.playlist_service import recommendation_reordered

    recommendation = recommend_playlist([track("/a.flac"), track("/b.flac"), track("/c.flac")], "build")
    original = [item.path for item in recommendation.ordered_tracks]

    result = recommendation_reordered(recommendation, list(reversed(original)))

    assert sorted(item.path for item in result.ordered_tracks) == sorted(original)


def test_recommendation_reordered_returns_unchanged_for_the_same_order() -> None:
    from xfinaudio.recommendation.playlist_service import recommendation_reordered

    recommendation = recommend_playlist([track("/a.flac"), track("/b.flac")], "build")
    same = [item.path for item in recommendation.ordered_tracks]

    assert recommendation_reordered(recommendation, same) is recommendation


def test_recommendation_reordered_rejects_an_order_that_is_not_a_permutation() -> None:
    """A partial or padded list is a caller bug, not an edit.

    Honouring it would silently drop or invent tracks; the DJ would export a
    crate that does not match what the screen showed.
    """
    from xfinaudio.recommendation.playlist_service import recommendation_reordered

    recommendation = recommend_playlist([track("/a.flac"), track("/b.flac")], "build")

    assert recommendation_reordered(recommendation, ["/a.flac"]) is recommendation
    assert recommendation_reordered(recommendation, ["/a.flac", "/b.flac", "/ghost.flac"]) is recommendation
    assert recommendation_reordered(recommendation, ["/a.flac", "/a.flac"]) is recommendation


def test_recommendation_reordered_honours_spectral_cohesion() -> None:
    from xfinaudio.recommendation.playlist_service import recommendation_reordered

    recommendation = recommend_playlist(
        [
            spectral_track("/left.flac", "RED"),
            spectral_track("/middle.flac", "GREEN"),
            spectral_track("/right.flac", "RED").model_copy(update={"energy_level": 7}),
        ],
        "build",
        spectral_cohesion=1.0,
    )
    flipped = list(reversed([item.path for item in recommendation.ordered_tracks]))

    without = recommendation_reordered(recommendation, flipped, spectral_cohesion=0.0)
    with_cohesion = recommendation_reordered(recommendation, flipped, spectral_cohesion=1.0)

    assert with_cohesion.transition_scores[0].total_score != without.transition_scores[0].total_score


def test_expected_set_length_sizes_the_arc_by_the_slot() -> None:
    from xfinaudio.recommendation.playlist_service import _expected_set_length

    assert _expected_set_length([], 30.0, 120.0, None) == 15
    assert _expected_set_length([], 60.0, 120.0, None) == 30
    assert _expected_set_length([], None, None, 12) == 12
    assert _expected_set_length([], None, None, None) is None


def test_expected_set_length_falls_back_to_the_mean_duration() -> None:
    """With no segment length each track counts in full."""
    from xfinaudio.recommendation.playlist_service import _expected_set_length

    pool = [track(f"/t{index}.flac").model_copy(update={"duration": 300.0}) for index in range(4)]

    assert _expected_set_length(pool, 30.0, None, None) == 6


# ---------------------------------------------------------------------------
# Reachability and the sequencing shortlist.
# ---------------------------------------------------------------------------


def test_reachability_keeps_a_chain_the_pool_order_would_have_broken() -> None:
    from xfinaudio.recommendation.playlist_service import _bpm_reachable_from

    interleaved = [120.0, 124.0, 121.0, 125.0, 122.0, 126.0, 123.0, 127.0]
    pool = [track(f"/c{i}.flac", bpm=bpm, camelot_key="8A", energy_level=5) for i, bpm in enumerate(interleaved)]

    _, dropped = _bpm_reachable_from(pool, "/c0.flac")

    assert dropped == 0, "every track chains to the anchor through 120-121-122..."


def test_reachability_drops_what_no_chain_can_reach() -> None:
    from xfinaudio.recommendation.playlist_service import _bpm_reachable_from

    pool = [
        track("/anchor.flac", bpm=120.0, camelot_key="8A", energy_level=5),
        track("/near.flac", bpm=121.0, camelot_key="8A", energy_level=5),
        track("/island.flac", bpm=190.0, camelot_key="8A", energy_level=5),
    ]

    kept, dropped = _bpm_reachable_from(pool, "/anchor.flac")

    assert [item.path for item in kept] == ["/anchor.flac", "/near.flac"]
    assert dropped == 1


def test_reachability_does_not_depend_on_candidate_order() -> None:
    """The whole point: the same pool must give the same answer every time."""
    import random as _random

    from xfinaudio.recommendation.playlist_service import _bpm_reachable_from

    bpms = [120.0, 121.0, 122.0, 123.0, 160.0, 190.0, 191.0]
    pool = [track(f"/t{i}.flac", bpm=bpm, camelot_key="8A", energy_level=5) for i, bpm in enumerate(bpms)]

    answers = {
        tuple(sorted(item.path for item in _bpm_reachable_from(shuffled, "/t0.flac")[0]))
        for shuffled in (_random.Random(seed).sample(pool, len(pool)) for seed in range(6))
    }

    assert len(answers) == 1, f"order changed the answer: {answers}"


def test_reachability_keeps_tracks_without_a_bpm() -> None:
    from xfinaudio.recommendation.playlist_service import _bpm_reachable_from

    pool = [
        track("/anchor.flac", bpm=120.0, camelot_key="8A", energy_level=5),
        track("/no-bpm.flac", bpm=None, camelot_key="8A", energy_level=5),
        track("/far.flac", bpm=190.0, camelot_key="8A", energy_level=5),
    ]

    kept, _ = _bpm_reachable_from(pool, "/anchor.flac")

    assert "/no-bpm.flac" in {item.path for item in kept}


def test_a_playable_track_survives_a_fast_one_earlier_in_the_pool() -> None:
    """The old gate lost this track for its position, not for its tempo."""
    tracks = [
        track("/manual.flac", bpm=100.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
        track("/too-fast.flac", bpm=140.0, camelot_key="8A", energy_level=2, genre="Disco", tags=["Disco"]),
        track("/ok.flac", bpm=101.0, camelot_key="8A", energy_level=5, genre="Disco", tags=["Disco"]),
    ]

    result = recommend_playlist(tracks, "warmup", controls=DJControls(manual_order_paths=["/manual.flac"]))

    assert "/ok.flac" in [item.path for item in result.ordered_tracks]


def test_shortlist_scales_with_the_slot_and_always_keeps_controls() -> None:
    from xfinaudio.recommendation.playlist_service import _shortlist_for_sequencing

    pool = [track(f"/t{index:03d}.flac", bpm=120.0, camelot_key="8A", energy_level=5) for index in range(200)]

    short = _shortlist_for_sequencing(pool, 15, preserve_paths={"/t199.flac"})
    long_slot = _shortlist_for_sequencing(pool, 40, preserve_paths=set())

    assert len(short) == 60
    assert "/t199.flac" in {item.path for item in short}, "a control track must survive the cap"
    assert len(long_slot) > len(short), "a longer slot earns more candidates"


def test_shortlist_caps_a_caller_that_names_no_slot() -> None:
    """`prep_copilot` sequences three variants for the DJ to skim, not one set to play.

    Bought at the cheap end of the cost curve: 0.035s per sequence against
    0.305s at 60 candidates, for 0.814 mean transition quality against 0.863.
    """
    from xfinaudio.recommendation.playlist_service import _shortlist_for_sequencing

    pool = [track(f"/t{index:03d}.flac", bpm=120.0, camelot_key="8A", energy_level=5) for index in range(200)]

    assert len(_shortlist_for_sequencing(pool, None)) == 30


def test_strategies_that_declare_an_arc_go_through_the_optimizer() -> None:
    """`recommend_sequence` is the only place a shape is applied."""
    pool = [
        track(f"/e{index}.flac", bpm=120.0 + index * 0.4, camelot_key="8A", energy_level=level)
        for index, level in enumerate([7, 2, 6, 3, 5, 4])
    ]

    for name in ("warmup", "build", "peak_time"):
        assert recommend_playlist(pool, name).optimizer != "strategy-order", name


def test_chill_keeps_its_sort() -> None:
    """Holding one low level is its whole point; sequencing buys it nothing."""
    pool = [
        track(f"/e{index}.flac", bpm=120.0 + index * 0.4, camelot_key="8A", energy_level=level)
        for index, level in enumerate([7, 2, 6, 3, 5, 4])
    ]

    assert recommend_playlist(pool, "chill").optimizer == "strategy-order"


# ---------------------------------------------------------------------------
# Genre is a property of the set, not of the strategy.
#
# It was only ever inferred from the anchor, and only when `same_genre` was
# picked -- so locking a set to one genre meant giving up the energy shape.
# "peak time, but Rock" could not be asked for. The DJ plays 30-minute blocks
# and changes genre between them, which is exactly the request this refuses.
# ---------------------------------------------------------------------------


def _mixed_genre_pool() -> list[TrackRecord]:
    return [
        track(f"/{genre.lower()}-{index}.flac", bpm=120.0 + index * 0.4, camelot_key="8A", energy_level=7, genre=genre)
        for genre in ("Rock", "House")
        for index in range(6)
    ]


def test_a_set_can_be_locked_to_a_genre_without_giving_up_its_shape() -> None:
    recommendation = recommend_playlist(_mixed_genre_pool(), "peak_time", controls=DJControls(genre="Rock"))

    genres = {(item.genre or "") for item in recommendation.ordered_tracks}
    assert genres == {"Rock"}
    assert recommendation.optimizer != "strategy-order", "the shape still goes through the optimizer"


def test_the_genre_choice_is_reported() -> None:
    recommendation = recommend_playlist(_mixed_genre_pool(), "peak_time", controls=DJControls(genre="Rock"))

    assert any("Rock" in warning for warning in recommendation.warnings)


def test_genre_matching_ignores_case_and_padding() -> None:
    recommendation = recommend_playlist(_mixed_genre_pool(), "peak_time", controls=DJControls(genre="  rock "))

    assert {(item.genre or "") for item in recommendation.ordered_tracks} == {"Rock"}


def test_control_tracks_survive_the_genre_filter() -> None:
    """The DJ pinned it on purpose; the filter does not overrule that."""
    pool = _mixed_genre_pool()

    recommendation = recommend_playlist(
        pool, "peak_time", controls=DJControls(genre="Rock", start_path="/house-0.flac")
    )

    assert "/house-0.flac" in [item.path for item in recommendation.ordered_tracks]


def test_a_genre_with_nothing_in_it_warns_rather_than_returning_an_empty_set() -> None:
    """Classical holds 27 tracks in the reference library and cannot fill a slot."""
    recommendation = recommend_playlist(_mixed_genre_pool(), "peak_time", controls=DJControls(genre="Polka"))

    assert recommendation.ordered_tracks, "an unmatchable genre must not silently empty the set"
    assert any("Polka" in warning for warning in recommendation.warnings)


def test_no_genre_asked_for_changes_nothing() -> None:
    without = recommend_playlist(_mixed_genre_pool(), "peak_time")
    explicit = recommend_playlist(_mixed_genre_pool(), "peak_time", controls=DJControls())

    assert len(without.ordered_tracks) == len(explicit.ordered_tracks)
    assert len({(item.genre or "") for item in without.ordered_tracks}) > 1


def test_a_genre_too_thin_to_fill_the_slot_says_so() -> None:
    """Classical holds 27 tracks in the reference library and yields a 2-track set.

    "Genre locked to 'Classical'" is true and useless on its own: the DJ asked
    for a 30-minute slot and got four minutes, and nothing said why.
    """
    pool = [
        *[
            track(f"/rock-{i}.flac", bpm=120.0 + i * 0.3, camelot_key="8A", energy_level=7, genre="Rock")
            for i in range(30)
        ],
        *[
            track(f"/classical-{i}.flac", bpm=120.0 + i * 0.3, camelot_key="8A", energy_level=7, genre="Classical")
            for i in range(3)
        ],
    ]

    recommendation = recommend_playlist(
        pool,
        "peak_time",
        controls=DJControls(genre="Classical"),
        target_duration_minutes=30.0,
        played_seconds_per_track=120.0,
    )

    assert any("Classical" in warning and "short" in warning.lower() for warning in recommendation.warnings), (
        f"no warning explains the short set: {recommendation.warnings}"
    )


def test_a_genre_that_fills_the_slot_stays_quiet_about_it() -> None:
    pool = [
        track(f"/rock-{i}.flac", bpm=120.0 + i * 0.3, camelot_key="8A", energy_level=7, genre="Rock") for i in range(40)
    ]

    recommendation = recommend_playlist(
        pool,
        "peak_time",
        controls=DJControls(genre="Rock"),
        target_duration_minutes=30.0,
        played_seconds_per_track=120.0,
    )

    assert not any("short" in warning.lower() for warning in recommendation.warnings)


# ---------------------------------------------------------------------------
# Characterization safety net: pins CURRENT behavior of _apply_energy_tolerance
# and the shared _apply_color_filter fallback so later slices can prove they
# did not break the untouched same_color / same_energy strategies. These tests
# assert today's behavior verbatim; they intentionally add no new behavior.
# ---------------------------------------------------------------------------


def _energy_track(path: str, energy: int | None) -> TrackRecord:
    return track(path, energy_level=energy)


def test_apply_energy_tolerance_keeps_plus_minus_one_band() -> None:
    strategy = get_strategy("same_energy")
    candidates = [
        _energy_track("/e6.flac", 6),
        _energy_track("/e7.flac", 7),
        _energy_track("/e8.flac", 8),
        _energy_track("/e9.flac", 9),
        _energy_track("/e10.flac", 10),
    ]

    filtered, warnings = _apply_energy_tolerance(candidates, strategy, anchor_energy=8, preserve_paths=set())

    kept = {t.path for t in filtered}
    assert kept == {"/e7.flac", "/e8.flac", "/e9.flac"}
    assert "/e6.flac" not in kept
    assert "/e10.flac" not in kept
    assert warnings == ["Filtered 2 track(s) outside same_energy energy tolerance"]


def test_apply_energy_tolerance_preserve_paths_bypass_the_band() -> None:
    strategy = get_strategy("same_energy")
    candidates = [
        _energy_track("/anchor.flac", 8),
        _energy_track("/faraway.flac", 1),
        _energy_track("/also_far.flac", 10),
    ]

    filtered, warnings = _apply_energy_tolerance(
        candidates, strategy, anchor_energy=8, preserve_paths={"/faraway.flac"}
    )

    kept = {t.path for t in filtered}
    # /faraway.flac is out of band but preserved; /also_far.flac is dropped.
    assert "/faraway.flac" in kept
    assert "/also_far.flac" not in kept
    assert kept == {"/anchor.flac", "/faraway.flac"}
    assert warnings == ["Filtered 1 track(s) outside same_energy energy tolerance"]


def test_apply_energy_tolerance_none_tolerance_returns_input_unchanged() -> None:
    # peak_time has no energy_tolerance set (None), which is the bypass case.
    strategy = get_strategy("peak_time")
    assert strategy.energy_tolerance is None
    candidates = [
        _energy_track("/e1.flac", 1),
        _energy_track("/e10.flac", 10),
    ]

    filtered, warnings = _apply_energy_tolerance(candidates, strategy, anchor_energy=5, preserve_paths=set())

    assert filtered is candidates
    assert warnings == []


def test_apply_energy_tolerance_no_removal_emits_no_warning() -> None:
    strategy = get_strategy("same_energy")
    candidates = [
        _energy_track("/e7.flac", 7),
        _energy_track("/e8.flac", 8),
        _energy_track("/e9.flac", 9),
    ]

    filtered, warnings = _apply_energy_tolerance(candidates, strategy, anchor_energy=8, preserve_paths=set())

    assert {t.path for t in filtered} == {"/e7.flac", "/e8.flac", "/e9.flac"}
    assert warnings == []


def test_apply_color_filter_same_color_falls_back_to_unfiltered_pool() -> None:
    # Anchor color is RED (from the start_path control), but no candidate is RED,
    # so the eligible pool is empty and the shared helper returns the original,
    # unfiltered `tracks` list plus the exact fallback warning.
    anchor = spectral_track("/anchor.flac", "RED")
    candidates = [
        anchor,
        spectral_track("/green.flac", "GREEN"),
        spectral_track("/blue.flac", "BLUE"),
    ]
    controls = DJControls(start_path="/anchor.flac")

    filtered, warnings = _apply_color_filter(
        candidates, controls, preserve_paths={"/anchor.flac"}, strategy_name="same_color"
    )

    assert filtered is candidates
    assert warnings == [
        "same_color filter applied: RED",
        "same_color: no candidates match anchor color 'RED'; falling back to unfiltered scoring",
    ]


def test_apply_color_filter_same_color_keeps_matching_candidates() -> None:
    anchor = spectral_track("/anchor.flac", "RED")
    candidates = [
        anchor,
        spectral_track("/red2.flac", "RED"),
        spectral_track("/green.flac", "GREEN"),
    ]
    controls = DJControls(start_path="/anchor.flac")

    filtered, warnings = _apply_color_filter(
        candidates, controls, preserve_paths={"/anchor.flac"}, strategy_name="same_color"
    )

    assert {t.path for t in filtered} == {"/anchor.flac", "/red2.flac"}
    assert warnings == ["same_color filter applied: RED"]


# ---------------------------------------------------------------------------
# tighten-same-color-energy Phase 2/3: strict combined eligibility.
# _same_color_energy_eligible(anchor, candidate) — exact energy + label equality
# for RED/GREEN/BLUE, and label equality PLUS a bounded RGB L1 / centroid /
# rolloff proximity gate for MIXED. Empty strict pools fail closed; controls are
# always preserved. These assert the NEW behavior this change introduces.
# ---------------------------------------------------------------------------


def _mixed_track(
    path: str,
    *,
    energy: int | None = 5,
    red: float,
    green: float,
    blue: float,
    centroid: float,
    rolloff: float,
) -> TrackRecord:
    return track(path, energy_level=energy).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=red,
                green_ratio=green,
                blue_ratio=blue,
                centroid_hz=centroid,
                rolloff_hz=rolloff,
                dominant_color="MIXED",
            )
        }
    )


# RGB band ratios that classify as each dominant color under `_dominant_color`
# (RED >= 0.45, GREEN >= 0.48, BLUE >= 0.22). Non-MIXED anchors now also flow
# through the bounded proximity gate, which needs finite positive centroid and
# rolloff denominators; `spectral_track` leaves both at 0.0, so gate tests use
# this helper instead.
_COLOR_RATIOS: dict[ColorName, tuple[float, float, float]] = {
    "RED": (0.70, 0.20, 0.10),
    "GREEN": (0.20, 0.70, 0.10),
    "BLUE": (0.20, 0.20, 0.60),
}


def _colored_track(
    path: str,
    color: ColorName,
    *,
    energy: int | None = 5,
    centroid: float = 1000.0,
    rolloff: float = 2000.0,
    red: float | None = None,
    green: float | None = None,
    blue: float | None = None,
) -> TrackRecord:
    base_red, base_green, base_blue = _COLOR_RATIOS[color]
    return track(path, energy_level=energy).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=base_red if red is None else red,
                green_ratio=base_green if green is None else green,
                blue_ratio=base_blue if blue is None else blue,
                centroid_hz=centroid,
                rolloff_hz=rolloff,
                dominant_color=color,
            )
        }
    )


def test_same_color_energy_eligible_requires_exact_energy_for_rgb() -> None:
    anchor = _colored_track("/anchor.flac", "RED", energy=5)
    same = _colored_track("/same.flac", "RED", energy=5)
    off_by_one = _colored_track("/off.flac", "RED", energy=6)

    assert _same_color_energy_eligible(anchor, same) is True
    assert _same_color_energy_eligible(anchor, off_by_one) is False


def test_same_color_energy_eligible_requires_label_equality_for_rgb() -> None:
    anchor = _colored_track("/anchor.flac", "RED", energy=5)
    other_color = _colored_track("/green.flac", "GREEN", energy=5)

    assert _same_color_energy_eligible(anchor, other_color) is False


def test_color_gate_constants_are_colour_neutral_with_unchanged_values() -> None:
    # tighten-spectral-color-filters slice A: the gate spans all colours, so the
    # constants carry colour-neutral names and no MIXED_-prefixed gate constant
    # remains. Values stay at the calibration-provisional defaults.
    import xfinaudio.recommendation.playlist_service as service

    assert COLOR_RGB_L1_MAX == 0.08
    assert COLOR_CENTROID_REL_MAX == 0.15
    assert COLOR_ROLLOFF_REL_MAX == 0.15
    assert not hasattr(service, "MIXED_RGB_L1_MAX")
    assert not hasattr(service, "MIXED_CENTROID_REL_MAX")
    assert not hasattr(service, "MIXED_ROLLOFF_REL_MAX")


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
def test_same_color_energy_eligible_admits_proximate_rgb_candidate(color: ColorName) -> None:
    # tighten-spectral-color-filters slice A: the bounded proximity gate now spans
    # every dominant-color label. A same-label same-energy candidate INSIDE the gate
    # is admitted for RED, GREEN and BLUE anchors alike.
    anchor = _colored_track("/anchor.flac", color, energy=5, centroid=1000.0, rolloff=2000.0)
    inside = _colored_track("/inside.flac", color, energy=5, centroid=1010.0, rolloff=2020.0)

    assert _same_color_energy_eligible(anchor, inside) is True


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
def test_same_color_energy_eligible_rejects_rgb_candidate_beyond_rgb_l1(color: ColorName) -> None:
    # Anchor-relative RGB L1 beyond COLOR_RGB_L1_MAX rejects the candidate even
    # though it shares the label and exact energy — no longer sufficient for RGB.
    base_red, base_green, base_blue = _COLOR_RATIOS[color]
    over = COLOR_RGB_L1_MAX / 2.0 + 0.05
    anchor = _colored_track("/anchor.flac", color, energy=5, centroid=1000.0, rolloff=2000.0)
    far = _colored_track(
        "/far.flac",
        color,
        energy=5,
        centroid=1000.0,
        rolloff=2000.0,
        red=base_red + over,
        green=base_green - over,
        blue=base_blue,
    )

    assert _same_color_energy_eligible(anchor, far) is False


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
def test_same_color_energy_eligible_rgb_centroid_and_rolloff_at_inclusive_bounds(color: ColorName) -> None:
    # Centroid and rolloff exactly on their bounds are eligible (inclusive) for RGB
    # anchors. RGB ratios are held equal to the anchor here so the RGB L1 axis is a
    # clean zero; the RGB-L1 inclusive bound is asserted separately below.
    anchor = _colored_track("/anchor.flac", color, energy=5, centroid=1000.0, rolloff=2000.0)
    edge = _colored_track(
        "/edge.flac",
        color,
        energy=5,
        centroid=1000.0 * (1.0 + COLOR_CENTROID_REL_MAX),
        rolloff=2000.0 * (1.0 + COLOR_ROLLOFF_REL_MAX),
    )

    assert _same_color_energy_eligible(anchor, edge) is True


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
def test_same_color_energy_eligible_rgb_l1_at_inclusive_bound(color: ColorName) -> None:
    # A candidate whose anchor-relative RGB L1 equals COLOR_RGB_L1_MAX exactly is
    # eligible (inclusive). Only one band moves, by exactly the constant, so the
    # computed L1 is bit-identical to the value the gate compares against — no
    # floating-point overshoot can turn an at-bound case into a just-over one.
    base_red, base_green, base_blue = _COLOR_RATIOS[color]
    anchor = _colored_track("/anchor.flac", color, energy=5, centroid=1000.0, rolloff=2000.0)
    edge = _colored_track(
        "/edge.flac",
        color,
        energy=5,
        centroid=1000.0,
        rolloff=2000.0,
        red=base_red,
        green=base_green - COLOR_RGB_L1_MAX,
        blue=base_blue,
    )

    assert _same_color_energy_eligible(anchor, edge) is True


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
@pytest.mark.parametrize("axis", ["centroid", "rolloff"])
def test_same_color_energy_eligible_rgb_rejects_each_bound_plus_epsilon(color: ColorName, axis: str) -> None:
    # Each bound + epsilon on its own axis rejects the candidate, per colour.
    anchor = _colored_track("/anchor.flac", color, energy=5, centroid=1000.0, rolloff=2000.0)
    centroid = 1000.0 * (1.0 + COLOR_CENTROID_REL_MAX + 0.01) if axis == "centroid" else 1000.0
    rolloff = 2000.0 * (1.0 + COLOR_ROLLOFF_REL_MAX + 0.01) if axis == "rolloff" else 2000.0
    candidate = _colored_track("/over.flac", color, energy=5, centroid=centroid, rolloff=rolloff)

    assert _same_color_energy_eligible(anchor, candidate) is False


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
def test_same_color_energy_eligible_rgb_fails_closed_on_missing_profile(color: ColorName) -> None:
    anchor = _colored_track("/anchor.flac", color, energy=5)
    no_profile = track("/np.flac", energy_level=5)

    assert _same_color_energy_eligible(anchor, no_profile) is False


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
def test_same_color_energy_eligible_rgb_fails_closed_on_zero_rgb_sum(color: ColorName) -> None:
    anchor = _colored_track("/anchor.flac", color, energy=5)
    zero_sum = _colored_track("/zero.flac", color, energy=5, red=0.0, green=0.0, blue=0.0)

    assert _same_color_energy_eligible(anchor, zero_sum) is False


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
@pytest.mark.parametrize("axis", ["centroid", "rolloff"])
def test_same_color_energy_eligible_rgb_fails_closed_on_zero_denominator(color: ColorName, axis: str) -> None:
    # A zero or non-finite centroid/rolloff denominator on the anchor fails closed
    # for RGB anchors, not only MIXED.
    centroid = 0.0 if axis == "centroid" else 1000.0
    rolloff = 0.0 if axis == "rolloff" else 2000.0
    anchor = _colored_track("/anchor.flac", color, energy=5, centroid=centroid, rolloff=rolloff)
    candidate = _colored_track("/c.flac", color, energy=5, centroid=centroid, rolloff=rolloff)

    assert _same_color_energy_eligible(anchor, candidate) is False


@pytest.mark.parametrize("color", ["RED", "GREEN", "BLUE"])
def test_same_color_energy_eligible_rgb_fails_closed_on_non_finite_ratio(color: ColorName) -> None:
    anchor = _colored_track("/anchor.flac", color, energy=5)
    candidate = _colored_track("/c.flac", color, energy=5, centroid=float("inf"))

    assert _same_color_energy_eligible(anchor, candidate) is False


def test_same_color_energy_eligible_mixed_passes_at_inclusive_boundary() -> None:
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    # Exactly on each inclusive bound: RGB L1 == COLOR_RGB_L1_MAX, centroid rel ==
    # COLOR_CENTROID_REL_MAX, rolloff rel == COLOR_ROLLOFF_REL_MAX.
    l1_half = COLOR_RGB_L1_MAX / 2.0
    candidate = _mixed_track(
        "/edge.flac",
        red=0.40 + l1_half,
        green=0.40 - l1_half,
        blue=0.20,
        centroid=1000.0 * (1.0 + COLOR_CENTROID_REL_MAX),
        rolloff=2000.0 * (1.0 + COLOR_ROLLOFF_REL_MAX),
    )

    assert _same_color_energy_eligible(anchor, candidate) is True


def test_same_color_energy_eligible_mixed_fails_just_over_rgb_l1() -> None:
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    over = (COLOR_RGB_L1_MAX / 2.0) + 0.001
    candidate = _mixed_track(
        "/over.flac",
        red=0.40 + over,
        green=0.40 - over,
        blue=0.20,
        centroid=1000.0,
        rolloff=2000.0,
    )

    assert _same_color_energy_eligible(anchor, candidate) is False


def test_same_color_energy_eligible_mixed_fails_just_over_centroid() -> None:
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    candidate = _mixed_track(
        "/over.flac",
        red=0.40,
        green=0.40,
        blue=0.20,
        centroid=1000.0 * (1.0 + COLOR_CENTROID_REL_MAX + 0.01),
        rolloff=2000.0,
    )

    assert _same_color_energy_eligible(anchor, candidate) is False


def test_same_color_energy_eligible_mixed_fails_just_over_rolloff() -> None:
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    candidate = _mixed_track(
        "/over.flac",
        red=0.40,
        green=0.40,
        blue=0.20,
        centroid=1000.0,
        rolloff=2000.0 * (1.0 + COLOR_ROLLOFF_REL_MAX + 0.01),
    )

    assert _same_color_energy_eligible(anchor, candidate) is False


def test_same_color_energy_eligible_mixed_fails_closed_on_zero_rgb_sum() -> None:
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    zero_sum = _mixed_track("/zero.flac", red=0.0, green=0.0, blue=0.0, centroid=1000.0, rolloff=2000.0)

    assert _same_color_energy_eligible(anchor, zero_sum) is False


def test_same_color_energy_eligible_mixed_fails_closed_on_zero_centroid_denominator() -> None:
    # Anchor centroid is the denominator of the relative delta; zero fails closed.
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=0.0, rolloff=2000.0)
    candidate = _mixed_track("/c.flac", red=0.40, green=0.40, blue=0.20, centroid=0.0, rolloff=2000.0)

    assert _same_color_energy_eligible(anchor, candidate) is False


def test_same_color_energy_eligible_mixed_fails_closed_on_zero_rolloff_denominator() -> None:
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=0.0)
    candidate = _mixed_track("/c.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=0.0)

    assert _same_color_energy_eligible(anchor, candidate) is False


def test_same_color_energy_eligible_mixed_fails_closed_when_candidate_profile_missing() -> None:
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    no_profile = track("/np.flac", energy_level=5)

    assert _same_color_energy_eligible(anchor, no_profile) is False


def test_same_color_energy_applies_strict_filter_before_capping() -> None:
    # A candidate that would survive the pool cap on scan order but fails strict
    # eligibility must be excluded BEFORE capping, not merely trimmed afterwards.
    # Build many eligible RED E5 tracks plus one ineligible GREEN E5, and assert
    # the GREEN one never appears regardless of where the cap lands.
    anchor = spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5})
    reds = [spectral_track(f"/red-{i}.flac", "RED").model_copy(update={"energy_level": 5}) for i in range(40)]
    ineligible = spectral_track("/green.flac", "GREEN").model_copy(update={"energy_level": 5})
    pool = [anchor, ineligible, *reds]

    result = recommend_playlist(pool, "same_color_energy", controls=DJControls(start_path="/anchor.flac"))

    paths = {item.path for item in result.ordered_tracks}
    assert "/green.flac" not in paths
    for item in result.ordered_tracks:
        if item.path == "/anchor.flac":
            continue
        profile = item.spectral_profile
        assert profile is not None
        assert profile.dominant_color == "RED"
        assert item.energy_level == 5


def test_same_color_energy_compatible_different_key_stays_eligible() -> None:
    # Spec Requirement 1: Camelot independence. A strict-eligible candidate whose
    # key is compatible-but-different from the anchor is NOT excluded on key.
    anchor = spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5, "camelot_key": "8A"})
    compatible_diff_key = spectral_track("/friend.flac", "RED").model_copy(
        update={"energy_level": 5, "camelot_key": "9A"}
    )

    result = recommend_playlist(
        [anchor, compatible_diff_key], "same_color_energy", controls=DJControls(start_path="/anchor.flac")
    )

    assert "/friend.flac" in {item.path for item in result.ordered_tracks}


def test_same_color_energy_preserves_controls_that_fail_strict_eligibility() -> None:
    # Controls (locked/start/end/manual) pass through strict filtering unchanged,
    # keeping their positions even when they fail strict generated eligibility.
    tracks = [
        spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/red.flac", "RED").model_copy(update={"energy_level": 5}),
        spectral_track("/locked-green.flac", "GREEN").model_copy(update={"energy_level": 9}),
        spectral_track("/end-blue.flac", "BLUE").model_copy(update={"energy_level": 1}),
    ]
    controls = DJControls(start_path="/anchor.flac", end_path="/end-blue.flac", locked_paths={"/locked-green.flac"})

    result = recommend_playlist(tracks, "same_color_energy", controls=controls)

    assert {item.path for item in result.ordered_tracks} == {
        "/anchor.flac",
        "/red.flac",
        "/locked-green.flac",
        "/end-blue.flac",
    }


def test_same_color_energy_missing_anchor_energy_fails_closed_with_prerequisite_warning() -> None:
    # Anchor lacks an energy level: generated candidates must be empty and a
    # prerequisite warning is emitted (no widening to unfiltered scoring).
    anchor = spectral_track("/anchor.flac", "RED").model_copy(update={"energy_level": None})
    other = spectral_track("/red.flac", "RED").model_copy(update={"energy_level": 5})

    result = recommend_playlist([anchor, other], "same_color_energy", controls=DJControls(start_path="/anchor.flac"))

    paths = {item.path for item in result.ordered_tracks}
    assert "/red.flac" not in paths
    assert any("same_color_energy" in warning and "prerequisite" in warning.lower() for warning in result.warnings)


def test_same_color_energy_mixed_anchor_admits_only_proximate_candidates() -> None:
    # Spec scenario: every generated MIXED candidate must satisfy the label AND the
    # bounded proximity gate. A near MIXED candidate passes; a far one is excluded.
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    near = _mixed_track("/near.flac", red=0.41, green=0.39, blue=0.20, centroid=1010.0, rolloff=2020.0)
    far = _mixed_track("/far.flac", red=0.20, green=0.20, blue=0.60, centroid=4000.0, rolloff=8000.0)

    result = recommend_playlist(
        [anchor, near, far], "same_color_energy", controls=DJControls(start_path="/anchor.flac")
    )

    paths = {item.path for item in result.ordered_tracks}
    assert "/near.flac" in paths
    assert "/far.flac" not in paths


def test_same_color_energy_shortage_returns_only_eligible_and_warns() -> None:
    # F1 (tighten-same-color-energy verify): spec R5 scenario "Strict pool is
    # shorter than requested". A MIXED anchor with fewer eligible generated
    # candidates than requested generated slots must (a) return only strictly
    # eligible generated candidates -- never relaxing eligibility to fill slots --
    # and (b) emit a shortage warning naming the shortfall.
    anchor = _mixed_track("/anchor.flac", red=0.40, green=0.40, blue=0.20, centroid=1000.0, rolloff=2000.0)
    near_one = _mixed_track("/near_one.flac", red=0.41, green=0.39, blue=0.20, centroid=1010.0, rolloff=2020.0)
    near_two = _mixed_track("/near_two.flac", red=0.42, green=0.38, blue=0.20, centroid=1020.0, rolloff=2040.0)
    far = _mixed_track("/far.flac", red=0.20, green=0.20, blue=0.60, centroid=4000.0, rolloff=8000.0)

    # 1 control (start-path anchor) + target_count 5 => 4 requested generated slots,
    # but only 2 candidates are strictly eligible, so this drives the shortage branch.
    result = recommend_playlist(
        [anchor, near_one, near_two, far],
        "same_color_energy",
        controls=DJControls(start_path="/anchor.flac"),
        target_count=5,
    )

    generated = [item for item in result.ordered_tracks if item.path != "/anchor.flac"]
    generated_paths = {item.path for item in generated}
    # A shortage never relaxes eligibility: only the two proximate MIXED candidates
    # survive; the far one is excluded even though slots remain unfilled.
    assert generated_paths == {"/near_one.flac", "/near_two.flac"}
    assert "/far.flac" not in generated_paths
    # Every returned generated candidate is still strictly eligible against the anchor.
    for candidate in generated:
        assert _same_color_energy_eligible(anchor, candidate) is True
        assert candidate.energy_level == anchor.energy_level
        assert candidate.spectral_profile is not None
        assert candidate.spectral_profile.dominant_color == "MIXED"

    # The exact shortage warning the implementation emits (2 eligible, 4 requested).
    assert any(
        warning == "same_color_energy: strict eligibility left 2 generated candidate(s) for 4 requested slot(s)"
        for warning in result.warnings
    )
