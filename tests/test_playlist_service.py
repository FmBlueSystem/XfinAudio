from unittest.mock import patch

from xfinaudio.audio.spectral_profile import ColorName, SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    _spectral_jump_warnings,
    recommend_playlist,
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


def test_start_path_survives_bpm_guard_without_crash() -> None:
    # The anchor (start_path) sorts last by path and has a large BPM gap from its predecessor,
    # so the adjacent-BPM-jump guard would drop it and crash the optimizer with "Unknown start_path".
    a = track("/aaa.flac", bpm=120.0)
    b = track("/bbb.flac", bpm=121.0)
    start = track("/zzz.flac", bpm=160.0)
    controls = DJControls(start_path="/zzz.flac")

    result = recommend_playlist([a, b, start], "harmonic_journey", controls=controls)

    assert "/zzz.flac" in {item.path for item in result.ordered_tracks}
    assert result.ordered_tracks[0].path == "/zzz.flac"


def test_chill_is_optimizer_backed_for_harmonic_coherence() -> None:
    # chill must sequence harmonically (via the optimizer), not by raw ascending BPM, so a filled
    # chill set keeps Camelot-compatible adjacencies instead of clashing keys.
    tracks = [
        track("/a.flac", bpm=100.0, camelot_key="8A", energy_level=3),
        track("/b.flac", bpm=102.0, camelot_key="3B", energy_level=3),
        track("/c.flac", bpm=101.0, camelot_key="9A", energy_level=3),
    ]

    result = recommend_playlist(tracks, "chill")

    assert result.optimizer != "strategy-order"
    assert len(result.ordered_tracks) == 3


def test_peak_time_is_optimizer_backed_for_harmonic_coherence() -> None:
    # peak_time only constrains energy (7-10); ordering should be harmonic, not raw energy sort.
    tracks = [
        track("/a.flac", bpm=128.0, camelot_key="8A", energy_level=9),
        track("/b.flac", bpm=129.0, camelot_key="3B", energy_level=8),
        track("/c.flac", bpm=128.5, camelot_key="9A", energy_level=10),
    ]

    result = recommend_playlist(tracks, "peak_time")

    assert result.optimizer != "strategy-order"
    assert len(result.ordered_tracks) == 3


def test_warmup_keeps_energy_non_decreasing() -> None:
    # Energy-constrained harmonic sequencing must preserve the ascending energy curve.
    tracks = [
        track("/a.flac", bpm=120.0, camelot_key="8A", energy_level=5),
        track("/b.flac", bpm=120.0, camelot_key="9A", energy_level=2),
        track("/c.flac", bpm=120.0, camelot_key="8B", energy_level=4),
        track("/d.flac", bpm=120.0, camelot_key="10A", energy_level=3),
    ]

    result = recommend_playlist(tracks, "warmup")

    energies = [t.energy_level for t in result.ordered_tracks]
    assert energies == [2, 3, 4, 5]  # non-decreasing energy curve preserved


def test_warmup_prefers_harmonic_adjacency_within_energy_tier() -> None:
    # All same energy: ordering should chain Camelot-compatible keys instead of raw path order.
    # 8A is compatible with 9A and 8B, but not with 3B.
    tracks = [
        track("/x.flac", bpm=120.0, camelot_key="8A", energy_level=3),
        track("/y.flac", bpm=120.0, camelot_key="3B", energy_level=3),
        track("/z.flac", bpm=120.0, camelot_key="9A", energy_level=3),
    ]

    result = recommend_playlist(tracks, "warmup")

    paths = [t.path for t in result.ordered_tracks]
    # Deterministic start at lowest path (/x, 8A); harmonic greedy picks /z (9A) before /y (3B).
    assert paths == ["/x.flac", "/z.flac", "/y.flac"]


def test_warmup_sequencing_is_deterministic() -> None:
    tracks = [
        track("/a.flac", camelot_key="8A", energy_level=2),
        track("/b.flac", camelot_key="9A", energy_level=3),
        track("/c.flac", camelot_key="10A", energy_level=4),
    ]
    first = recommend_playlist(tracks, "warmup").ordered_tracks
    second = recommend_playlist(tracks, "warmup").ordered_tracks
    assert [t.path for t in first] == [t.path for t in second]


def test_dj_controls_rejects_equal_start_and_end() -> None:
    import pytest

    from xfinaudio.recommendation.controls import DJControls

    with pytest.raises(ValueError):
        DJControls(start_path="/a.flac", end_path="/a.flac")
