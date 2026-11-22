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


def _recommendation(track_count: int, *, root: Path, strategy: str = "harmonic_journey") -> PlaylistRecommendation:
    tracks = [
        TrackRecord(
            path=str(root / "dd" / "_Lossless" / f"Track {index:02d}.flac"),
            title=f"Track {index:02d}",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
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


def test_a_typed_name_keeps_its_exact_parent_name_and_its_children_follow_it(tmp_path: Path) -> None:
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

    # A typed or saved name keeps today's exact-name semantics: a confirmed export
    # replaces the parent it names and keeps the backup copy instead.
    assert plan.parent.crate_name == "Sesión del viernes"
    assert plan.parent.target_path == existing
    assert plan.parent.backup_path == existing.with_name(f"{existing.name}.bak")
    assert [child.crate_name for child in plan.children] == [
        "Sesión del viernes%%1 (1-2)",
        "Sesión del viernes%%2 (3-4)",
        "Sesión del viernes%%3 (5-6)",
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
    # A flat typed name nests under nothing, exactly as today.
    assert flat.ancestor_names == ()
    assert flat.missing_ancestor_names == ()


def test_the_crate_tree_plan_and_planner_are_exported_from_the_package_api() -> None:
    from xfinaudio.exporting import SeratoCrateTreePlan as exported_plan  # noqa: PLC0415
    from xfinaudio.exporting import plan_serato_crate_tree as exported_planner  # noqa: PLC0415
    from xfinaudio.exporting.serato_playlist_exporter import SeratoCrateTreePlan  # noqa: PLC0415

    assert exported_planner is plan_serato_crate_tree
    assert exported_plan is SeratoCrateTreePlan
