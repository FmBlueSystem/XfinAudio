from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import recommend_playlist


def complete_track(path: str, bpm: float, energy: int, key: str = "8A") -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        metadata_status="complete",
    )


def test_build_quality_report_summarizes_transition_metrics() -> None:
    recommendation = recommend_playlist(
        [
            complete_track("/music/a.flac", 120.0, 3, "8A"),
            complete_track("/music/b.flac", 123.0, 6, "8A"),
            complete_track("/music/c.flac", 126.0, 7, "9A"),
        ],
        "harmonic_journey",
    )

    report = build_quality_report(recommendation)

    assert report.track_count == 3
    assert report.transition_count == 2
    assert report.average_transition_score == round(recommendation.total_score / 2, 6)
    assert report.bpm_jumps == [3.0, 3.0]
    assert report.energy_jumps == [3, 1]
    assert report.warning_count == sum(len(score.warnings) for score in recommendation.transition_scores)


def test_build_quality_report_compares_manual_path_sequence() -> None:
    recommendation = recommend_playlist(
        [
            complete_track("/music/a.flac", 120.0, 3),
            complete_track("/music/b.flac", 121.0, 4),
            complete_track("/music/c.flac", 122.0, 5),
        ],
        "harmonic_journey",
    )
    manual_paths = [recommendation.ordered_tracks[0].path, recommendation.ordered_tracks[2].path, "/music/missing.flac"]

    report = build_quality_report(recommendation, manual_paths=manual_paths)

    assert report.manual_overlap_ratio == round(2 / 3, 6)
    assert report.manual_order_match_prefix_count == 1
