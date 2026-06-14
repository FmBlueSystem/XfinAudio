from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import recommend_playlist


def complete_track(
    path: str,
    bpm: float,
    energy: int,
    key: str = "8A",
    spectral_profile: SpectralProfile | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        metadata_status="complete",
        spectral_profile=spectral_profile,
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


def test_recommend_playlist_warns_on_red_to_green_spectral_shift() -> None:
    red = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    green = SpectralProfile(red_ratio=0.05, green_ratio=0.9, blue_ratio=0.05, dominant_color="GREEN")
    recommendation = recommend_playlist(
        [
            complete_track("/music/red.flac", 120.0, 5, "8A", spectral_profile=red),
            complete_track("/music/green.flac", 120.0, 5, "8A", spectral_profile=green),
        ],
        "harmonic_journey",
    )

    assert any("Spectral shift" in warning for warning in recommendation.warnings)


def test_recommend_playlist_does_not_warn_when_adjacent_colors_match() -> None:
    green = SpectralProfile(red_ratio=0.05, green_ratio=0.9, blue_ratio=0.05, dominant_color="GREEN")
    recommendation = recommend_playlist(
        [
            complete_track("/music/green1.flac", 120.0, 5, "8A", spectral_profile=green),
            complete_track("/music/green2.flac", 120.0, 5, "8A", spectral_profile=green),
        ],
        "harmonic_journey",
    )

    assert not any("Spectral shift" in warning for warning in recommendation.warnings)


def test_recommend_playlist_does_not_warn_when_spectral_profile_is_missing() -> None:
    recommendation = recommend_playlist(
        [
            complete_track("/music/a.flac", 120.0, 5, "8A", spectral_profile=None),
            complete_track("/music/b.flac", 120.0, 5, "8A", spectral_profile=None),
        ],
        "harmonic_journey",
    )

    assert not any("Spectral shift" in warning for warning in recommendation.warnings)
