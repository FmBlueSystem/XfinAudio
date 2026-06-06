from datetime import datetime
from pathlib import Path

from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes, write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    discover_serato_libraries,
    plan_generated_serato_playlist_export,
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    plan_serato_playlist_export,
    select_serato_library_for_tracks,
    to_serato_crate_path,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


def _recommendation(paths: list[str]) -> PlaylistRecommendation:
    tracks = [
        TrackRecord(
            path=path,
            title=Path(path).stem,
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        )
        for path in paths
    ]
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=[],
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


def test_discover_serato_libraries_finds_home_and_external_volume_roots(tmp_path: Path) -> None:
    home = tmp_path / "home" / "freddy"
    volumes_root = tmp_path / "Volumes"
    home_serato = home / "Music" / "_Serato_"
    dd_serato = volumes_root / "dd" / "_Serato_"
    passport_serato = volumes_root / "My Passport" / "_Serato_"
    for serato in [home_serato, dd_serato, passport_serato]:
        (serato / "Subcrates").mkdir(parents=True)

    libraries = discover_serato_libraries(home=home, volumes_root=volumes_root)

    assert [library.serato_folder for library in libraries] == [home_serato, dd_serato, passport_serato]
    assert all(library.subcrates_folder == library.serato_folder / "Subcrates" for library in libraries)


def test_to_serato_crate_path_converts_absolute_mac_paths_to_drive_relative_paths() -> None:
    assert to_serato_crate_path(Path("/Volumes/dd/_Lossless/a.flac")) == "_Lossless/a.flac"
    assert to_serato_crate_path(Path("/Users/freddymolina/Music/a.wav")) == "Users/freddymolina/Music/a.wav"


def test_select_serato_library_prefers_the_volume_that_contains_playlist_tracks(tmp_path: Path) -> None:
    volumes_root = tmp_path / "Volumes"
    dd_serato = volumes_root / "dd" / "_Serato_"
    passport_serato = volumes_root / "My Passport" / "_Serato_"
    for serato in [dd_serato, passport_serato]:
        (serato / "Subcrates").mkdir(parents=True)
    libraries = discover_serato_libraries(home=tmp_path / "home", volumes_root=volumes_root)

    selected = select_serato_library_for_tracks(
        [volumes_root / "dd" / "_Lossless" / "a.flac", volumes_root / "dd" / "_Lossless" / "b.flac"],
        libraries,
    )

    assert selected.serato_folder == dd_serato


def test_plan_serato_playlist_export_builds_confirmed_writable_crate_for_recommendation(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _recommendation(
        [str(tmp_path / "dd" / "_Lossless" / "A.flac"), str(tmp_path / "dd" / "_Lossless" / "B.flac")]
    )

    plan = plan_serato_playlist_export("XfinAudio Recommended", recommendation, serato_folder)

    assert plan.target_path == serato_folder / "Subcrates" / "XfinAudio Recommended.crate"
    assert plan.relative_paths == ("_Lossless/A.flac", "_Lossless/B.flac")
    assert plan.preview()["will_write"] is False

    result = write_serato_crate(plan, confirm=True)
    parsed = parse_serato_crate_bytes(result.written_path.read_bytes())

    assert result.validated is True
    assert parsed.paths == ("_Lossless/A.flac", "_Lossless/B.flac")


def test_plan_serato_playlist_export_preserves_detected_home_volume_root(tmp_path: Path) -> None:
    serato_folder = tmp_path / "Users" / "freddy" / "Music" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    library = SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path)
    recommendation = _recommendation([str(tmp_path / "Users" / "freddy" / "Music" / "Track.wav")])

    plan = plan_serato_playlist_export("Home Test", recommendation, library)

    assert plan.relative_paths == ("Users/freddy/Music/Track.wav",)


def test_plan_generated_serato_playlist_export_groups_crate_by_strategy(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _recommendation(
        [str(tmp_path / "dd" / "_Lossless" / "Stayin Alive.flac"), str(tmp_path / "dd" / "_Lossless" / "B.flac")]
    )

    plan = plan_generated_serato_playlist_export(
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 3, 5, 0),
    )

    assert plan.target_path == (
        serato_folder / "Subcrates" / "XfinAudio%%Build%%20260606-030500 - build - Stayin Alive - 2 tracks.crate"
    )
    assert plan.backup_path == plan.target_path.with_name(f"{plan.target_path.name}.bak")
    assert plan.relative_paths == ("_Lossless/Stayin Alive.flac", "_Lossless/B.flac")


def test_plan_generated_serato_playlist_export_avoids_existing_crate_collision(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    target_folder = serato_folder / "Subcrates"
    target_folder.mkdir(parents=True)
    existing = target_folder / "XfinAudio%%Build%%20260606-030500 - build - Track - 1 track.crate"
    existing.write_bytes(b"existing")
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])

    plan = plan_generated_serato_playlist_export(
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 3, 5, 0),
    )

    assert plan.target_path == target_folder / "XfinAudio%%Build%%20260606-030500 - build - Track - 1 track-2.crate"
    assert existing.read_bytes() == b"existing"


def test_plan_metadata_status_serato_export_groups_incomplete_worklist(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Needs Key.flac"),
            title="Needs Key",
            bpm=120,
            metadata_status="incomplete",
            missing_required_fields=["camelot_key", "energy_level"],
        ),
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Ready.flac"),
            title="Ready",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
    ]

    plan = plan_metadata_status_serato_export(
        records,
        "incomplete",
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 4, 20, 0),
    )

    assert plan.target_path == (
        serato_folder
        / "Subcrates"
        / "XfinAudio%%Metadata%%Incomplete%%20260606-042000 - incomplete metadata - 1 track.crate"
    )
    assert plan.relative_paths == ("_Lossless/Needs Key.flac",)


def test_plan_metadata_missing_field_serato_export_groups_specific_worklist(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Needs Key.flac"),
            title="Needs Key",
            metadata_status="incomplete",
            missing_required_fields=["camelot_key"],
        ),
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Needs Energy.flac"),
            title="Needs Energy",
            metadata_status="incomplete",
            missing_required_fields=["energy_level"],
        ),
    ]

    plan = plan_metadata_missing_field_serato_export(
        records,
        "camelot_key",
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 4, 45, 0),
    )

    assert plan.target_path == (
        serato_folder / "Subcrates" / "XfinAudio%%Metadata%%Missing Key%%20260606-044500 - missing key - 1 track.crate"
    )
    assert plan.relative_paths == ("_Lossless/Needs Key.flac",)


def test_select_serato_library_prefers_specific_external_volume_over_home_root(tmp_path: Path) -> None:
    home_serato = tmp_path / "Users" / "freddy" / "Music" / "_Serato_"
    dd_serato = tmp_path / "Volumes" / "dd" / "_Serato_"
    for serato in [home_serato, dd_serato]:
        (serato / "Subcrates").mkdir(parents=True)
    libraries = [
        SeratoLibrary(serato_folder=home_serato, volume_root=tmp_path),
        SeratoLibrary(serato_folder=dd_serato, volume_root=tmp_path / "Volumes" / "dd"),
    ]

    selected = select_serato_library_for_tracks(
        [tmp_path / "Volumes" / "dd" / "_Lossless" / "Track.flac"],
        libraries,
    )

    assert selected.serato_folder == dd_serato


def test_serato_playlist_planners_are_exported_from_package_api() -> None:
    """Package-level exporting API exposes the Serato playlist planners."""
    from xfinaudio.exporting import (  # noqa: PLC0415
        plan_generated_serato_playlist_export as generated_export,
    )
    from xfinaudio.exporting import (
        plan_metadata_missing_field_serato_export as missing_field_export,
    )
    from xfinaudio.exporting import (
        plan_metadata_status_serato_export as status_export,
    )

    assert generated_export is plan_generated_serato_playlist_export
    assert missing_field_export is plan_metadata_missing_field_serato_export
    assert status_export is plan_metadata_status_serato_export


def test_plan_copilot_variant_serato_playlist_export_groups_by_strategy_and_variant(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_playlist_exporter import plan_copilot_variant_serato_playlist_export

    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _recommendation(
        [str(tmp_path / "dd" / "_Lossless" / "Stayin Alive.flac"), str(tmp_path / "dd" / "_Lossless" / "B.flac")]
    )

    plan = plan_copilot_variant_serato_playlist_export(
        "balanced",
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    assert plan.target_path == (
        serato_folder
        / "Subcrates"
        / "XfinAudio%%Prep Copilot%%Build%%Balanced%%20260606-143000 - build - balanced - Stayin Alive - 2 tracks.crate"
    )
    assert plan.relative_paths == ("_Lossless/Stayin Alive.flac", "_Lossless/B.flac")


def test_plan_copilot_variant_serato_playlist_export_avoids_existing_crate_collision(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_playlist_exporter import plan_copilot_variant_serato_playlist_export

    serato_folder = tmp_path / "dd" / "_Serato_"
    target_folder = serato_folder / "Subcrates"
    target_folder.mkdir(parents=True)
    existing = (
        target_folder / "XfinAudio%%Prep Copilot%%Build%%Safe%%20260606-143000 - build - safe - Track - 1 track.crate"
    )
    existing.write_bytes(b"existing")
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])

    plan = plan_copilot_variant_serato_playlist_export(
        "safe",
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    assert plan.target_path == (
        target_folder / "XfinAudio%%Prep Copilot%%Build%%Safe%%20260606-143000 - build - safe - Track - 1 track-2.crate"
    )
    assert existing.read_bytes() == b"existing"
