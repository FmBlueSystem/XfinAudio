"""Tests for the playlist build log (construction provenance)."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.build_log import (
    BuildStage,
    PlaylistBuildLog,
    build_genre_relations,
    count_cross_genre,
)


def _track(path: str, genre: str | None) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        bpm=124.0,
        camelot_key="8A",
        energy_level=5,
        genre=genre,
        metadata_status="complete",
    )


def test_build_genre_relations_classifies_each_adjacency() -> None:
    ordered = [
        _track("a", "House, Disco"),
        _track("b", "House, Funk"),  # shares 'house' -> overlap (not identical token set)
        _track("c", "House"),  # b={house,funk} vs c={house} -> overlap
        _track("d", "Techno"),  # c={house} vs d={techno} -> cross
    ]

    relations = build_genre_relations(ordered)

    assert [r.relation for r in relations] == ["overlap", "overlap", "cross"]
    assert relations[0].order == 1
    assert relations[0].from_track == "a"
    assert relations[0].to_track == "b"


def test_build_genre_relations_marks_identical_token_sets_same() -> None:
    ordered = [_track("a", "Techno"), _track("b", "Techno")]
    relations = build_genre_relations(ordered)
    assert [r.relation for r in relations] == ["same"]


def test_build_genre_relations_ignores_missing_genre_as_cross_none() -> None:
    ordered = [_track("a", None), _track("b", "Techno")]
    relations = build_genre_relations(ordered)
    # No judgeable genre on one side -> relation 'unknown', not counted as cross.
    assert relations[0].relation == "unknown"
    assert count_cross_genre(relations) == 0


def test_count_cross_genre_counts_only_cross() -> None:
    ordered = [
        _track("a", "House"),
        _track("b", "Techno"),  # cross
        _track("c", "Techno"),  # same
    ]
    relations = build_genre_relations(ordered)
    assert count_cross_genre(relations) == 1


def test_playlist_build_log_reconciles_final_stage_with_track_count() -> None:
    stages = [
        BuildStage(name="input", input_count=100, output_count=100, dropped=0, reason=""),
        BuildStage(name="complete_metadata", input_count=100, output_count=80, dropped=20, reason="incomplete"),
        BuildStage(name="final", input_count=80, output_count=12, dropped=68, reason="sequenced"),
    ]
    log = PlaylistBuildLog(
        strategy="harmonic_journey",
        optimizer="two-opt",
        pool_size=100,
        stages=stages,
        genre_relations=[],
        cross_genre_count=0,
        final_track_count=12,
        warnings=[],
    )
    assert log.stages[-1].output_count == log.final_track_count
