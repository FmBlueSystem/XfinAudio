"""Tests for RecommendationPresenter — pool selection logic extracted from MainWindow."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import build_recommendation_pool
from xfinaudio.recommendation.controls import DJControls


def _record(
    path: str, bpm: float | None = None, genre: str | None = None, tags: list[str] | None = None
) -> TrackRecord:
    return TrackRecord(
        path=path,
        metadata_status="complete",
        bpm=bpm,
        genre=genre,
        tags=tags or [],
    )


def test_build_pool_returns_all_complete_records_within_limit():
    records = [_record(f"/{i}.mp3") for i in range(5)]
    result = build_recommendation_pool(records, controls=None, limit=25)
    assert len(result) == 5


def test_build_pool_excludes_incomplete_records():
    complete = _record("/a.mp3")
    incomplete = TrackRecord(path="/b.mp3", metadata_status="incomplete", missing_required_fields=["bpm"])
    result = build_recommendation_pool([complete, incomplete], controls=None, limit=25)
    assert all(r.path == "/a.mp3" for r in result)


def test_build_pool_respects_limit():
    records = [_record(f"/{i}.mp3") for i in range(30)]
    result = build_recommendation_pool(records, controls=None, limit=25)
    assert len(result) == 25


def test_build_pool_prioritizes_control_tracks():
    priority = _record("/priority.mp3")
    others = [_record(f"/{i}.mp3") for i in range(10)]
    controls = DJControls(start_path="/priority.mp3")
    result = build_recommendation_pool([*others, priority], controls=controls, limit=25)
    assert result[0].path == "/priority.mp3"


def test_build_pool_no_duplicates_when_priority_overlaps():
    track = _record("/a.mp3")
    controls = DJControls(start_path="/a.mp3")
    result = build_recommendation_pool([track], controls=controls, limit=25)
    assert len(result) == 1


def test_build_pool_genre_compatible_records_ranked_before_fallback():
    anchor = _record("/anchor.mp3", genre="techno")
    compatible = _record("/compat.mp3", genre="techno")
    unrelated = _record("/unrelated.mp3", genre="jazz")
    controls = DJControls(start_path="/anchor.mp3")
    result = build_recommendation_pool([anchor, compatible, unrelated], controls=controls, limit=25)
    paths = [r.path for r in result]
    assert paths.index("/compat.mp3") < paths.index("/unrelated.mp3")


def test_pool_prefers_bpm_feasible_candidate_over_generic_tag_overlap() -> None:
    anchor = _record(
        "/anchor.mp3",
        bpm=102.0,
        genre="Hip-Hop & R&B",
        tags=["hip-hop", "r&b", "party"],
    )
    fast_more_tags = _record(
        "/fast.mp3",
        bpm=126.0,
        genre="Hip-Hop & R&B",
        tags=["hip-hop", "r&b", "party", "club", "radio"],
    )
    close_fewer_tags = _record(
        "/close.mp3",
        bpm=103.0,
        genre="Hip-Hop & R&B",
        tags=["hip-hop", "r&b"],
    )
    controls = DJControls(start_path="/anchor.mp3")
    result = build_recommendation_pool([anchor, fast_more_tags, close_fewer_tags], controls=controls, limit=25)
    paths = [r.path for r in result]
    assert paths.index("/close.mp3") < paths.index("/fast.mp3")


def test_build_pool_treats_invalid_candidate_camelot_key_as_incompatible() -> None:
    anchor = _record("/anchor.mp3", bpm=120.0, genre="House", tags=["peak"])
    anchor = anchor.model_copy(update={"camelot_key": "8A", "energy_level": 5})
    invalid_key = _record("/invalid.mp3", bpm=120.0, genre="House", tags=["peak"])
    invalid_key = invalid_key.model_copy(update={"camelot_key": "bad-key", "energy_level": 5})
    compatible_key = _record("/compatible.mp3", bpm=120.0, genre="House", tags=["peak"])
    compatible_key = compatible_key.model_copy(update={"camelot_key": "8A", "energy_level": 5})

    result = build_recommendation_pool(
        [anchor, invalid_key, compatible_key],
        controls=DJControls(start_path="/anchor.mp3"),
        limit=25,
    )

    paths = [track.path for track in result]
    assert paths.index("/compatible.mp3") < paths.index("/invalid.mp3")
