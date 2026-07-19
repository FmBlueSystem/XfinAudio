from unittest.mock import patch

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    _bpm_jump_warning,
    _spectral_jump_warnings,
    prefilter_strategy_candidates,
    recommend_playlist,
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
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path.rsplit("/", maxsplit=1)[-1],
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        genre=genre,
        tags=["Peak"] if tags is None else tags,
        metadata_status=status,  # type: ignore[arg-type]
    )


def spectral_track(path: str, color: ColorName) -> TrackRecord:
    return track(path).model_copy(
        update={
            "spectral_profile": SpectralProfile(
                red_ratio=1.0 if color == "RED" else 0.0,
                green_ratio=1.0 if color == "GREEN" else 0.0,
                blue_ratio=1.0 if color == "BLUE" else 0.0,
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
    assert (
        "same_color: no candidates match anchor color 'RED'; falling back to unfiltered scoring" in result.warnings
    )


def test_same_color_skips_filter_when_no_track_has_a_profile() -> None:
    tracks = [track("/a.flac"), track("/b.flac")]

    result = recommend_playlist(tracks, "same_color")

    assert {item.path for item in result.ordered_tracks} == {"/a.flac", "/b.flac"}
    assert not any(warning.startswith("same_color") for warning in result.warnings)


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
