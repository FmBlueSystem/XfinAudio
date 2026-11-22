from datetime import datetime
from pathlib import Path

import pytest

from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    plan_generated_serato_playlist_export,
    plan_serato_crate_tree,
    plan_serato_playlist_export,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry

GENERATED_AT = datetime(2026, 11, 14, 3, 5, 0)
PARENT_NAME = "XfinAudio%%Harmonic Journey 14-nov"
# A twenty-track journey: a quiet opening, a long climb, a three-track peak, a long tail.
# Its four phases are tracks 1-4, 5-9, 10-12 and 13-20 (see test_serato_crate_phases.py).
JOURNEY = (4, 4, 4, 4, 4, 6, 7, 8, 9, 10, 10, 10, 9, 8, 7, 6, 5, 4, 4, 4)
FLAT = (5, 6, 5, 6, 5, 6, 5, 6, 5, 6, 5, 6, 5, 6, 5, 6, 5, 6, 5, 6)


def _recommendation(
    track_count: int,
    *,
    root: Path,
    strategy: str = "harmonic_journey",
    energies: tuple[int | None, ...] | None = None,
) -> PlaylistRecommendation:
    levels = energies if energies is not None else (5,) * track_count
    tracks = [
        TrackRecord(
            path=str(root / "dd" / "_Lossless" / f"Track {index:02d}.flac"),
            title=f"Track {index:02d}",
            bpm=120.0,
            camelot_key="8A",
            energy_level=levels[index - 1],
            metadata_status="complete",
        )
        for index in range(1, track_count + 1)
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


def _subcrates(tmp_path: Path) -> tuple[Path, SeratoLibrary]:
    serato_folder = tmp_path / "dd" / "_Serato_"
    subcrates = serato_folder / "Subcrates"
    subcrates.mkdir(parents=True)
    return subcrates, SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd")


def test_a_twenty_track_set_splits_into_one_parent_and_four_ordered_children(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)
    recommendation = _recommendation(20, root=tmp_path)

    plan = plan_serato_crate_tree(
        recommendation,
        library,
        segment_size=5,
        generated_at=GENERATED_AT,
    )

    assert plan.parent.crate_name == PARENT_NAME
    assert plan.parent.target_path == subcrates / f"{PARENT_NAME}.crate"
    assert plan.parent.relative_paths == tuple(f"_Lossless/Track {index:02d}.flac" for index in range(1, 21))
    assert [child.crate_name for child in plan.children] == [
        f"{PARENT_NAME}%%1 (1-5)",
        f"{PARENT_NAME}%%2 (6-10)",
        f"{PARENT_NAME}%%3 (11-15)",
        f"{PARENT_NAME}%%4 (16-20)",
    ]
    assert [child.target_path.name for child in plan.children] == [
        f"{PARENT_NAME}%%1 (1-5).crate",
        f"{PARENT_NAME}%%2 (6-10).crate",
        f"{PARENT_NAME}%%3 (11-15).crate",
        f"{PARENT_NAME}%%4 (16-20).crate",
    ]
    assert all(child.target_path.parent == subcrates for child in plan.children)
    assert all(
        child.backup_path == child.target_path.with_name(f"{child.target_path.name}.bak") for child in plan.children
    )
    assert plan.plans == (plan.parent, *plan.children)

    for index, child in enumerate(plan.children):
        expected = plan.parent.relative_paths[index * 5 : (index + 1) * 5]
        assert child.relative_paths == expected
        assert child.track_count == 5
        assert parse_serato_crate_bytes(child.crate_bytes).paths == expected

    # Planning writes nothing: the DJ still has to confirm the export.
    assert list(subcrates.iterdir()) == []


def test_a_twenty_two_track_set_keeps_a_shorter_last_child(tmp_path: Path) -> None:
    _subcrates_path, library = _subcrates(tmp_path)
    recommendation = _recommendation(22, root=tmp_path)

    plan = plan_serato_crate_tree(recommendation, library, segment_size=5, generated_at=GENERATED_AT)

    assert len(plan.children) == 5
    assert [child.crate_name for child in plan.children] == [
        f"{PARENT_NAME}%%1 (1-5)",
        f"{PARENT_NAME}%%2 (6-10)",
        f"{PARENT_NAME}%%3 (11-15)",
        f"{PARENT_NAME}%%4 (16-20)",
        f"{PARENT_NAME}%%5 (21-22)",
    ]
    assert plan.children[-1].relative_paths == ("_Lossless/Track 21.flac", "_Lossless/Track 22.flac")
    assert plan.parent.track_count == 22


def test_an_existing_automatic_name_moves_the_whole_tree_to_the_next_number(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)
    older_parent = subcrates / f"{PARENT_NAME}.crate"
    older_parent.write_bytes(b"an older export")
    recommendation = _recommendation(12, root=tmp_path)

    plan = plan_serato_crate_tree(recommendation, library, segment_size=5, generated_at=GENERATED_AT)

    numbered = f"{PARENT_NAME} (2)"
    assert plan.parent.crate_name == numbered
    assert plan.parent.target_path == subcrates / f"{numbered}.crate"
    assert [child.crate_name for child in plan.children] == [
        f"{numbered}%%1 (1-5)",
        f"{numbered}%%2 (6-10)",
        f"{numbered}%%3 (11-12)",
    ]
    # No child of this export lands under the older export's parent.
    assert not any((subcrates / child.target_path.name).exists() for child in plan.children)
    assert list(subcrates.iterdir()) == [older_parent]
    assert older_parent.read_bytes() == b"an older export"


def test_a_orphan_child_of_the_next_number_moves_the_whole_tree_further(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)
    # An older export took the base name, and a `(2)` child is left over without its
    # parent: the new tree must skip `(2)` instead of adopting a child it did not write.
    (subcrates / f"{PARENT_NAME}.crate").write_bytes(b"an older export")
    (subcrates / f"{PARENT_NAME} (2)%%1 (1-5).crate").write_bytes(b"orphan child")
    recommendation = _recommendation(6, root=tmp_path)

    plan = plan_serato_crate_tree(recommendation, library, segment_size=5, generated_at=GENERATED_AT)

    numbered = f"{PARENT_NAME} (3)"
    assert plan.parent.crate_name == numbered
    assert plan.children[0].crate_name == f"{numbered}%%1 (1-5)"


def test_a_typed_name_nests_the_whole_tree_under_the_parent_and_its_children_follow_it(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)
    existing = subcrates / "Sesión del viernes.crate"
    existing.write_bytes(b"an earlier export the DJ named")
    recommendation = _recommendation(6, root=tmp_path)

    plan = plan_serato_crate_tree(
        recommendation,
        library,
        crate_name="Sesión del viernes",
        segment_size=2,
        generated_at=GENERATED_AT,
    )

    # A typed or saved name lives under the XfinAudio parent crate and keeps the exact-name
    # semantics there: a confirmed export replaces the parent it names and keeps the backup.
    assert plan.parent.crate_name == "XfinAudio%%Sesión del viernes"
    assert plan.parent.target_path == subcrates / "XfinAudio%%Sesión del viernes.crate"
    assert plan.parent.backup_path == subcrates / "XfinAudio%%Sesión del viernes.crate.bak"
    # The crate already at the Serato root is another crate: it is neither the target nor touched.
    assert plan.parent.target_path != existing
    assert existing.read_bytes() == b"an earlier export the DJ named"
    assert [child.crate_name for child in plan.children] == [
        "XfinAudio%%Sesión del viernes%%1 (1-2)",
        "XfinAudio%%Sesión del viernes%%2 (3-4)",
        "XfinAudio%%Sesión del viernes%%3 (5-6)",
    ]


def test_without_a_split_the_plan_is_todays_single_crate_plan(tmp_path: Path) -> None:
    _subcrates_path, library = _subcrates(tmp_path)
    recommendation = _recommendation(7, root=tmp_path)

    tree = plan_serato_crate_tree(recommendation, library, generated_at=GENERATED_AT)
    generated = plan_generated_serato_playlist_export(recommendation, library, generated_at=GENERATED_AT)
    typed_tree = plan_serato_crate_tree(recommendation, library, crate_name="Mi sesión")
    typed = plan_serato_playlist_export("Mi sesión", recommendation, library)

    assert tree.children == ()
    assert tree.parent == generated
    assert typed_tree.children == ()
    assert typed_tree.parent == typed


def test_a_segment_size_not_smaller_than_the_set_produces_the_parent_only(tmp_path: Path) -> None:
    _subcrates_path, library = _subcrates(tmp_path)

    exact = plan_serato_crate_tree(
        _recommendation(20, root=tmp_path), library, segment_size=20, generated_at=GENERATED_AT
    )
    larger = plan_serato_crate_tree(
        _recommendation(3, root=tmp_path), library, segment_size=50, generated_at=GENERATED_AT
    )
    generated = plan_generated_serato_playlist_export(
        _recommendation(20, root=tmp_path), library, generated_at=GENERATED_AT
    )

    # With N >= track count there is nothing to split: the parent holds the set and
    # the plan is the same single crate a DJ without a split gets.
    assert exact.children == ()
    assert exact.parent == generated
    assert larger.children == ()


@pytest.mark.parametrize("segment_size", [1, 0, -3, 51, 2.5, "5", True])
def test_an_invalid_segment_size_is_refused_with_a_clear_error(tmp_path: Path, segment_size: object) -> None:
    subcrates, library = _subcrates(tmp_path)
    recommendation = _recommendation(6, root=tmp_path)

    with pytest.raises(ValueError, match="segment size must be an integer between 2 and 50"):
        plan_serato_crate_tree(
            recommendation,
            library,
            segment_size=segment_size,  # type: ignore[arg-type]
            generated_at=GENERATED_AT,
        )

    assert list(subcrates.iterdir()) == []


def test_the_plan_names_the_ancestors_of_the_parent_it_still_needs(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)
    recommendation = _recommendation(6, root=tmp_path)

    missing = plan_serato_crate_tree(recommendation, library, segment_size=3, generated_at=GENERATED_AT)
    (subcrates / "XfinAudio.crate").write_bytes(b"already there")
    present = plan_serato_crate_tree(recommendation, library, segment_size=3, generated_at=GENERATED_AT)
    flat = plan_serato_crate_tree(recommendation, library, crate_name="Plana", segment_size=3)

    assert missing.ancestor_names == ("XfinAudio",)
    assert missing.missing_ancestor_names == ("XfinAudio",)
    assert present.ancestor_names == ("XfinAudio",)
    assert present.missing_ancestor_names == ()
    # A typed name nests under the XfinAudio parent crate like any other export, and this
    # test's folder already holds that parent.
    assert flat.ancestor_names == ("XfinAudio",)
    assert flat.missing_ancestor_names == ()


def test_the_crate_tree_plan_and_planner_are_exported_from_the_package_api() -> None:
    from xfinaudio.exporting import SeratoCrateTreePlan as exported_plan  # noqa: PLC0415
    from xfinaudio.exporting import plan_serato_crate_tree as exported_planner  # noqa: PLC0415
    from xfinaudio.exporting.serato_playlist_exporter import SeratoCrateTreePlan  # noqa: PLC0415

    assert exported_planner is plan_serato_crate_tree
    assert exported_plan is SeratoCrateTreePlan


def test_a_phase_split_names_each_child_after_its_phase_under_the_parent(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)
    recommendation = _recommendation(20, root=tmp_path, energies=JOURNEY)

    plan = plan_serato_crate_tree(recommendation, library, crate_name="22 nov", split_mode="phases")

    assert plan.phase_reason is None
    assert plan.parent.crate_name == "XfinAudio%%22 nov"
    assert plan.parent.relative_paths == tuple(f"_Lossless/Track {index:02d}.flac" for index in range(1, 21))
    assert [child.crate_name for child in plan.children] == [
        "XfinAudio%%22 nov%%1 Apertura (1-4)",
        "XfinAudio%%22 nov%%2 Subida (5-9)",
        "XfinAudio%%22 nov%%3 Pico (10-12)",
        "XfinAudio%%22 nov%%4 Cierre (13-20)",
    ]
    assert [child.target_path.name for child in plan.children] == [
        "XfinAudio%%22 nov%%1 Apertura (1-4).crate",
        "XfinAudio%%22 nov%%2 Subida (5-9).crate",
        "XfinAudio%%22 nov%%3 Pico (10-12).crate",
        "XfinAudio%%22 nov%%4 Cierre (13-20).crate",
    ]
    assert all(child.target_path.parent == subcrates for child in plan.children)
    assert plan.plans == (plan.parent, *plan.children)
    # Every phase child holds exactly its own run of the ordered set, in the same order.
    assert [child.track_count for child in plan.children] == [4, 5, 3, 8]
    for child, (first, last) in zip(plan.children, [(1, 4), (5, 9), (10, 12), (13, 20)], strict=True):
        expected = tuple(f"_Lossless/Track {index:02d}.flac" for index in range(first, last + 1))
        assert child.relative_paths == expected
        assert parse_serato_crate_bytes(child.crate_bytes).paths == expected
    # Planning still writes nothing.
    assert list(subcrates.iterdir()) == []


def test_a_phase_split_of_an_automatic_name_moves_the_whole_tree_to_the_next_number(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)
    older_parent = subcrates / f"{PARENT_NAME}.crate"
    older_parent.write_bytes(b"an older export")
    recommendation = _recommendation(20, root=tmp_path, energies=JOURNEY)

    plan = plan_serato_crate_tree(recommendation, library, split_mode="phases", generated_at=GENERATED_AT)

    numbered = f"{PARENT_NAME} (2)"
    assert plan.parent.crate_name == numbered
    assert [child.crate_name for child in plan.children] == [
        f"{numbered}%%1 Apertura (1-4)",
        f"{numbered}%%2 Subida (5-9)",
        f"{numbered}%%3 Pico (10-12)",
        f"{numbered}%%4 Cierre (13-20)",
    ]
    assert list(subcrates.iterdir()) == [older_parent]
    assert older_parent.read_bytes() == b"an older export"


def test_a_phase_split_without_phases_exports_the_parent_only_and_says_why(tmp_path: Path) -> None:
    subcrates, library = _subcrates(tmp_path)

    flat = plan_serato_crate_tree(
        _recommendation(20, root=tmp_path, energies=FLAT), library, split_mode="phases", generated_at=GENERATED_AT
    )
    short = plan_serato_crate_tree(
        _recommendation(7, root=tmp_path, energies=JOURNEY[:7]), library, split_mode="phases", generated_at=GENERATED_AT
    )
    unmeasured = plan_serato_crate_tree(
        _recommendation(20, root=tmp_path, energies=(None,) * 20),
        library,
        split_mode="phases",
        generated_at=GENERATED_AT,
    )
    generated = plan_generated_serato_playlist_export(
        _recommendation(20, root=tmp_path, energies=FLAT), library, generated_at=GENERATED_AT
    )

    assert flat.children == ()
    assert flat.phase_reason == "flat"
    assert flat.parent == generated
    assert short.phase_reason == "too_few_tracks"
    assert unmeasured.phase_reason == "too_few_energies"
    assert list(subcrates.iterdir()) == []


def test_every_n_and_no_split_keep_todays_plan_and_name_no_phase_reason(tmp_path: Path) -> None:
    _subcrates_path, library = _subcrates(tmp_path)
    recommendation = _recommendation(20, root=tmp_path, energies=JOURNEY)
    generated = plan_generated_serato_playlist_export(recommendation, library, generated_at=GENERATED_AT)

    no_split = plan_serato_crate_tree(recommendation, library, generated_at=GENERATED_AT)
    explicit_segments = plan_serato_crate_tree(
        recommendation, library, split_mode="segments", generated_at=GENERATED_AT
    )
    absent_mode = plan_serato_crate_tree(recommendation, library, split_mode=None, generated_at=GENERATED_AT)
    every_three = plan_serato_crate_tree(recommendation, library, segment_size=3, generated_at=GENERATED_AT)

    assert no_split.parent == generated
    assert no_split.children == ()
    assert no_split.phase_reason is None
    # The energy of the tracks changes nothing when the DJ splits every N tracks.
    assert explicit_segments == no_split == absent_mode
    assert [child.crate_name for child in every_three.children] == [
        f"{PARENT_NAME}%%1 (1-3)",
        f"{PARENT_NAME}%%2 (4-6)",
        f"{PARENT_NAME}%%3 (7-9)",
        f"{PARENT_NAME}%%4 (10-12)",
        f"{PARENT_NAME}%%5 (13-15)",
        f"{PARENT_NAME}%%6 (16-18)",
        f"{PARENT_NAME}%%7 (19-20)",
    ]
    assert every_three.phase_reason is None


def test_a_segment_size_left_over_from_the_other_mode_changes_nothing_in_phases_mode(tmp_path: Path) -> None:
    _subcrates_path, library = _subcrates(tmp_path)
    recommendation = _recommendation(20, root=tmp_path, energies=JOURNEY)

    phases = plan_serato_crate_tree(recommendation, library, crate_name="22 nov", split_mode="phases")
    with_size = plan_serato_crate_tree(
        recommendation, library, crate_name="22 nov", segment_size=5, split_mode="phases"
    )

    # The phase split derives its own boundaries: the size field is disabled in that mode,
    # so a value still held by the options screen must not turn the tree into segments.
    assert with_size == phases


@pytest.mark.parametrize("split_mode", ["phase", "PHASES", "energy", "", 5, True])
def test_an_unknown_split_mode_is_refused_with_a_clear_error(tmp_path: Path, split_mode: object) -> None:
    subcrates, library = _subcrates(tmp_path)
    recommendation = _recommendation(20, root=tmp_path, energies=JOURNEY)

    with pytest.raises(ValueError, match="split mode must be segments or phases"):
        plan_serato_crate_tree(
            recommendation,
            library,
            split_mode=split_mode,  # type: ignore[arg-type]
            generated_at=GENERATED_AT,
        )

    assert list(subcrates.iterdir()) == []


def test_the_split_mode_validator_is_exported_from_the_package_api() -> None:
    from xfinaudio.exporting import validate_split_mode as exported_validator  # noqa: PLC0415
    from xfinaudio.exporting.serato_playlist_exporter import validate_split_mode  # noqa: PLC0415

    assert exported_validator is validate_split_mode
    assert validate_split_mode(None) == "segments"
    assert validate_split_mode("phases") == "phases"
