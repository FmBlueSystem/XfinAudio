import json

from xfinaudio.exporting.explainability import build_playlist_explanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import recommend_playlist


def complete_track(
    path: str,
    title: str,
    bpm: float,
    key: str,
    energy: int,
    tags: list[str] | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=f"Artist {title}",
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        tags=tags or [],
        genre="house",
        metadata_status="complete",
    )


def test_build_playlist_explanation_includes_transition_components_and_track_context() -> None:
    recommendation = recommend_playlist(
        [
            complete_track("/music/a.flac", "A", 124.0, "8A", 5, ["warm"]),
            complete_track("/music/b.flac", "B", 125.0, "8B", 6, ["warm"]),
            complete_track("/music/c.flac", "C", 128.0, "9B", 8, ["peak"]),
        ],
        "harmonic_journey",
    )

    report = build_playlist_explanation(recommendation)

    assert report.track_count == 3
    assert report.transition_count == 2
    assert [transition.order for transition in report.transitions] == [1, 2]
    first = report.transitions[0]
    assert first.left.path == recommendation.transition_scores[0].left_path
    assert first.right.path == recommendation.transition_scores[0].right_path
    assert first.final_score == recommendation.transition_scores[0].total_score
    assert set(first.component_scores) >= {"harmonic", "bpm", "energy", "tags"}
    assert first.explanations
    assert first.warnings == recommendation.transition_scores[0].warnings


def test_playlist_explanation_is_json_serializable_and_deterministic() -> None:
    recommendation = recommend_playlist(
        [
            complete_track("/music/a.flac", "A", 124.0, "8A", 5),
            complete_track("/music/b.flac", "B", 124.0, "8A", 5),
        ],
        "harmonic_journey",
    )

    first = build_playlist_explanation(recommendation).model_dump(mode="json")
    second = build_playlist_explanation(recommendation).model_dump(mode="json")

    assert first == second
    encoded = json.dumps(first, sort_keys=True)
    assert '"final_score"' in encoded
