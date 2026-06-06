from pathlib import Path

from xfinaudio.exporting.serato_crate import write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import SeratoLibrary, plan_generated_serato_playlist_export
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import build_dj_readiness_report, validate_serato_round_trip
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
from xfinaudio.recommendation.scoring import score_transition
from xfinaudio.recommendation.strategies import default_strategy_registry


def track(
    path: str,
    *,
    bpm: float = 120.0,
    key: str = "8A",
    energy: int = 5,
    genre: str | None = "House",
    tags: list[str] | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=Path(path).stem,
        artist="Artist",
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        genre=genre,
        tags=["Peak"] if tags is None else tags,
        metadata_status="complete",
    )


def manual_recommendation(tracks: list[TrackRecord]) -> PlaylistRecommendation:
    transitions = [score_transition(left, right) for left, right in zip(tracks, tracks[1:], strict=False)]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=transitions,
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="manual-test",
        total_score=sum(score.total_score for score in transitions),
    )


def test_dj_readiness_marks_clean_recommendation_ready() -> None:
    recommendation = recommend_playlist(
        [
            track("/music/a.flac", bpm=120, key="8A", energy=5),
            track("/music/b.flac", bpm=121, key="8A", energy=5),
            track("/music/c.flac", bpm=122, key="9A", energy=6),
        ],
        "harmonic_journey",
    )

    report = build_dj_readiness_report(recommendation, build_quality_report(recommendation))

    assert report.status == "ready"
    assert report.blocker_count == 0
    assert report.review_count == 0
    assert "Ready" in report.summary


def test_dj_readiness_blocks_impossible_bpm_jump() -> None:
    recommendation = manual_recommendation(
        [
            track("/music/a.flac", bpm=100, key="8A", energy=5),
            track("/music/b.flac", bpm=110, key="8A", energy=5),
        ]
    )

    report = build_dj_readiness_report(recommendation, build_quality_report(recommendation))

    assert report.status == "blocked"
    assert report.blocker_count == 1
    assert any(check.label == "BPM continuity" and check.status == "blocked" for check in report.checks)
    assert "10.00%" in report.summary


def test_dj_readiness_flags_genre_or_tag_warnings_for_review() -> None:
    recommendation = manual_recommendation(
        [
            track("/music/house.flac", bpm=120, key="8A", energy=5, genre="House", tags=["Peak"]),
            track("/music/rock.flac", bpm=121, key="8A", energy=5, genre="Rock", tags=["Guitar"]),
        ]
    )

    report = build_dj_readiness_report(recommendation, build_quality_report(recommendation))

    assert report.status == "needs_review"
    assert report.blocker_count == 0
    assert report.review_count >= 1
    assert any(check.label == "Transition warnings" and check.status == "needs_review" for check in report.checks)


def test_serato_round_trip_blocks_when_exported_crate_references_missing_files(tmp_path: Path) -> None:
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    existing_track = volume_root / "Music" / "existing.flac"
    existing_track.parent.mkdir(parents=True)
    existing_track.write_bytes(b"audio")
    missing_track = volume_root / "Music" / "missing.flac"
    recommendation = recommend_playlist(
        [
            track(str(existing_track), bpm=120, key="8A", energy=5),
            track(str(missing_track), bpm=121, key="8A", energy=5),
        ],
        "harmonic_journey",
    )
    plan = plan_generated_serato_playlist_export(
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=volume_root),
    )
    write_serato_crate(plan, confirm=True)

    check = validate_serato_round_trip(plan, volume_root=volume_root)

    assert check.status == "blocked"
    assert "1 unresolved track" in check.detail


def test_serato_round_trip_is_ready_when_written_crate_and_tracks_resolve(tmp_path: Path) -> None:
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    tracks = []
    for name, bpm in [("a.flac", 120), ("b.flac", 121)]:
        path = volume_root / "Music" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        tracks.append(track(str(path), bpm=bpm, key="8A", energy=5))
    recommendation = recommend_playlist(tracks, "harmonic_journey")
    plan = plan_generated_serato_playlist_export(
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=volume_root),
    )
    write_serato_crate(plan, confirm=True)

    check = validate_serato_round_trip(plan, volume_root=volume_root)

    assert check.status == "ready"
    assert "2 track(s) resolve" in check.detail


def test_export_dj_readiness_json_is_deterministic() -> None:
    from xfinaudio.quality.dj_readiness import export_dj_readiness_json

    recommendation = manual_recommendation(
        [
            track("/music/a.flac", bpm=100, key="8A", energy=5),
            track("/music/b.flac", bpm=110, key="8A", energy=5),
        ]
    )
    report = build_dj_readiness_report(recommendation, build_quality_report(recommendation))

    exported = export_dj_readiness_json(report)

    assert '"status": "blocked"' in exported
    assert '"blocker_count": 1' in exported
    assert '"label": "BPM continuity"' in exported
    assert exported.endswith("\n")


def test_export_dj_readiness_csv_has_stable_columns() -> None:
    from xfinaudio.quality.dj_readiness import export_dj_readiness_csv

    recommendation = manual_recommendation(
        [
            track("/music/a.flac", bpm=120, key="8A", energy=5),
            track("/music/b.flac", bpm=121, key="8A", energy=5),
        ]
    )
    report = build_dj_readiness_report(recommendation, build_quality_report(recommendation))

    exported = export_dj_readiness_csv(report)

    assert exported.splitlines()[0] == "check,status,detail"
    assert "BPM continuity,ready," in exported
    assert exported.endswith("\n")
