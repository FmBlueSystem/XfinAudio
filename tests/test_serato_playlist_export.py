from datetime import datetime
from pathlib import Path

import pytest

from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes, write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    _sanitize_name,
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


def _recommendation(paths: list[str], strategy: str = "build") -> PlaylistRecommendation:
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
        strategy=default_strategy_registry().get(strategy),
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

    plan = plan_serato_playlist_export("Warmup", recommendation, serato_folder)

    assert plan.target_path == serato_folder / "Subcrates" / "XfinAudio%%Warmup.crate"
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


def test_plan_generated_serato_playlist_export_names_crate_by_strategy_and_short_date(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _recommendation(
        [str(tmp_path / "dd" / "_Lossless" / "Stayin Alive.flac"), str(tmp_path / "dd" / "_Lossless" / "B.flac")],
        strategy="harmonic_journey",
    )

    plan = plan_generated_serato_playlist_export(
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 11, 14, 3, 5, 0),
    )

    assert plan.target_path == (serato_folder / "Subcrates" / "XfinAudio%%Harmonic Journey 14-nov.crate")
    # Style plus date is the whole name: no strategy sub-crate level and no anchor, count or stamp.
    assert plan.target_path.stem.split("%%") == ["XfinAudio", "Harmonic Journey 14-nov"]
    assert plan.backup_path == plan.target_path.with_name(f"{plan.target_path.name}.bak")
    assert plan.relative_paths == ("_Lossless/Stayin Alive.flac", "_Lossless/B.flac")


def test_plan_generated_serato_playlist_export_numbers_every_existing_short_name(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    target_folder = serato_folder / "Subcrates"
    target_folder.mkdir(parents=True)
    first = target_folder / "XfinAudio%%Build 14-nov.crate"
    first.write_bytes(b"existing")
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])
    library = SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd")

    second = plan_generated_serato_playlist_export(
        recommendation, library, generated_at=datetime(2026, 11, 14, 3, 5, 0)
    )

    assert second.target_path == target_folder / "XfinAudio%%Build 14-nov (2).crate"
    second.target_path.write_bytes(b"second")

    third = plan_generated_serato_playlist_export(recommendation, library, generated_at=datetime(2026, 11, 14, 3, 5, 0))

    assert third.target_path == target_folder / "XfinAudio%%Build 14-nov (3).crate"
    assert first.read_bytes() == b"existing"
    assert second.target_path.read_bytes() == b"second"


def test_generated_short_name_spells_the_export_month_in_spanish_without_a_leading_zero(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])
    library = SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd")
    months = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

    names = [
        plan_generated_serato_playlist_export(
            recommendation, library, generated_at=datetime(2026, month, 5, 22, 0, 0)
        ).target_path.stem
        for month in range(1, 13)
    ]

    assert names == [f"XfinAudio%%Build 5-{month}" for month in months]


def test_a_saved_playlist_name_lives_under_the_xfinaudio_parent_crate(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    root_crate = serato_folder / "Subcrates" / "22 nov.crate"
    root_crate.write_bytes(b"a crate the DJ made at the Serato root")
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])

    plan = plan_serato_playlist_export("22 nov", recommendation, serato_folder)

    # A saved playlist shares the one XfinAudio parent crate instead of landing on the root.
    assert plan.crate_name == "XfinAudio%%22 nov"
    assert plan.target_path == serato_folder / "Subcrates" / "XfinAudio%%22 nov.crate"
    assert plan.backup_path == serato_folder / "Subcrates" / "XfinAudio%%22 nov.crate.bak"
    # Planning writes nothing, and the crate at the root stays exactly as it was.
    assert not plan.target_path.exists()
    assert root_crate.read_bytes() == b"a crate the DJ made at the Serato root"


def test_a_typed_name_that_already_carries_the_parent_is_not_doubled(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])

    plan = plan_serato_playlist_export("XfinAudio%%22 nov", recommendation, serato_folder)

    assert plan.crate_name == "XfinAudio%%22 nov"
    assert plan.target_path == serato_folder / "Subcrates" / "XfinAudio%%22 nov.crate"


def test_a_typed_or_saved_playlist_name_is_used_unchanged_even_when_it_looks_automatic(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    target_folder = serato_folder / "Subcrates"
    target_folder.mkdir(parents=True)
    existing = target_folder / "XfinAudio%%Build 14-nov.crate"
    existing.write_bytes(b"earlier export")
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])

    plan = plan_serato_playlist_export("XfinAudio%%Build 14-nov", recommendation, serato_folder)

    # A name the user typed (or a saved playlist name) is never renumbered: a confirmed
    # export replaces it and keeps the backup copy instead.
    assert plan.target_path == existing
    assert plan.backup_path == existing.with_name(f"{existing.name}.bak")


def test_metadata_worklist_collision_keeps_the_unchanged_worklist_suffix(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    target_folder = serato_folder / "Subcrates"
    target_folder.mkdir(parents=True)
    records = [
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Needs Key.flac"),
            title="Needs Key",
            bpm=120,
            metadata_status="incomplete",
            missing_required_fields=["camelot_key"],
        )
    ]
    existing = target_folder / "XfinAudio%%Metadata%%Incomplete%%1 track · 0606-0420.crate"
    existing.write_bytes(b"existing")

    plan = plan_metadata_status_serato_export(
        records,
        "incomplete",
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 4, 20, 0),
    )

    # Metadata worklists are out of scope for the short names: same name, same old suffix.
    assert plan.target_path == target_folder / "XfinAudio%%Metadata%%Incomplete%%1 track · 0606-0420-2.crate"
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
        serato_folder / "Subcrates" / "XfinAudio%%Metadata%%Incomplete%%1 track · 0606-0420.crate"
    )
    assert plan.target_path.stem.rsplit("%%", 1) == ["XfinAudio%%Metadata%%Incomplete", "1 track · 0606-0420"]
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
        serato_folder / "Subcrates" / "XfinAudio%%Metadata%%Missing Key%%1 track · 0606-0445.crate"
    )
    assert plan.target_path.stem.rsplit("%%", 1) == ["XfinAudio%%Metadata%%Missing Key", "1 track · 0606-0445"]
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

    assert plan.target_path == (serato_folder / "Subcrates" / "XfinAudio%%Build 6-jun.crate")
    assert plan.target_path.stem.split("%%") == ["XfinAudio", "Build 6-jun"]
    assert plan.relative_paths == ("_Lossless/Stayin Alive.flac", "_Lossless/B.flac")


def test_plan_copilot_variant_serato_playlist_export_numbers_existing_crate_collision(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_playlist_exporter import plan_copilot_variant_serato_playlist_export

    serato_folder = tmp_path / "dd" / "_Serato_"
    target_folder = serato_folder / "Subcrates"
    target_folder.mkdir(parents=True)
    existing = target_folder / "XfinAudio%%Build 6-jun.crate"
    existing.write_bytes(b"existing")
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / "Track.flac")])

    plan = plan_copilot_variant_serato_playlist_export(
        "safe",
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    assert plan.target_path == (target_folder / "XfinAudio%%Build 6-jun (2).crate")
    assert existing.read_bytes() == b"existing"


def test_the_anchor_title_never_lengthens_a_generated_crate_name(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    title = "This Is An Exceptionally Long Anchor Title With Extra Words"
    recommendation = _recommendation([str(tmp_path / "dd" / "_Lossless" / f"{title}.flac")])

    plan = plan_generated_serato_playlist_export(
        recommendation,
        SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd"),
        generated_at=datetime(2026, 8, 9, 7, 2, 8),
    )

    assert plan.target_path.stem == "XfinAudio%%Build 9-ago"


def test_sanitize_name_removes_path_separators_and_rejects_empty_results() -> None:
    assert _sanitize_name("folder/name\\crate") == "folder-name-crate"

    with pytest.raises(ValueError, match="at least one safe character"):
        _sanitize_name(" ... ")


def test_parent_crate_names_of_a_nested_crate_are_its_ancestors_outermost_first() -> None:
    from xfinaudio.exporting.serato_playlist_exporter import parent_crate_names

    # Serato nests crates with `%%`, so «XfinAudio%%Harmonic Journey 14-nov» lives under «XfinAudio».
    assert parent_crate_names("XfinAudio%%Harmonic Journey 14-nov") == ("XfinAudio",)
    assert parent_crate_names("XfinAudio%%Metadata%%Pendientes") == ("XfinAudio", "XfinAudio%%Metadata")
    # A flat crate name needs no ancestor at all.
    assert parent_crate_names("Sesión guardada") == ()
    assert parent_crate_names("XfinAudio") == ()
