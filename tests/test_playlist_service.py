from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
from xfinaudio.recommendation.scoring import ScoringWeights
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


def test_recommend_playlist_uses_injected_strategy_registry() -> None:
    peak_as_custom = get_strategy("peak_time").model_copy(update={"name": "custom_peak"})
    registry = StrategyRegistry([peak_as_custom])
    tracks = [track("/low.flac", energy_level=3), track("/high.flac", energy_level=9)]

    result = recommend_playlist(tracks, "custom_peak", strategy_registry=registry)

    assert result.strategy.name == "custom_peak"
    assert [item.path for item in result.ordered_tracks] == ["/high.flac"]
