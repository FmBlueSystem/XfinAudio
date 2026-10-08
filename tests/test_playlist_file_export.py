"""Tests for UI-independent playlist file export planning."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from xfinaudio.exporting.playlist_file_export import plan_playlist_file_export
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


def _make_recommendation(paths: list[str]) -> PlaylistRecommendation:
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


def test_plan_playlist_file_export_uses_requested_name_and_traktor_extension(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    plan = plan_playlist_file_export(
        software="Traktor",
        recommendation=recommendation,
        safe_folder=tmp_path,
        requested_name="Warmup",
        variant_name="balanced",
    )

    assert plan.software == "Traktor"
    assert plan.target_name == "Warmup"
    assert plan.playlist_name == "Warmup"
    assert plan.target_path == tmp_path / "Warmup.nml"


def test_plan_playlist_file_export_uses_variant_name_when_requested_name_missing(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    plan = plan_playlist_file_export(
        software="Rekordbox",
        recommendation=recommendation,
        safe_folder=tmp_path,
        requested_name=None,
        variant_name="Balanced Variant",
    )

    assert plan.target_name == "Balanced Variant"
    assert plan.playlist_name == "Balanced Variant"
    assert plan.target_path == tmp_path / "Balanced Variant.xml"


def test_plan_playlist_file_export_uses_generated_name_with_software_suffix(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    plan = plan_playlist_file_export(
        software="VirtualDJ",
        recommendation=recommendation,
        safe_folder=tmp_path,
        requested_name=None,
        variant_name=None,
        generated_at=datetime(2024, 3, 10, 8, 0, 0),
    )

    assert plan.target_name == "20240310_080000_build_virtualdj_1_track"
    assert plan.playlist_name == plan.target_name
    assert plan.target_path == tmp_path / "20240310_080000_build_virtualdj_1_track.xml"


def test_plan_playlist_file_export_rejects_unknown_software(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    with pytest.raises(ValueError, match="Unknown export software: Ableton"):
        plan_playlist_file_export(
            software="Ableton",
            recommendation=recommendation,
            safe_folder=tmp_path,
            requested_name=None,
            variant_name=None,
        )


def test_plan_playlist_file_export_keeps_absolute_requested_name_inside_safe_folder(tmp_path: Path) -> None:
    """An absolute requested name must never redirect the write outside the safe folder."""
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])
    safe_folder = tmp_path / "safe"

    plan = plan_playlist_file_export(
        software="Rekordbox",
        recommendation=recommendation,
        safe_folder=safe_folder,
        requested_name="/etc/evil.xml",
        variant_name=None,
    )

    assert plan.target_name == "evil.xml"
    assert plan.target_path == safe_folder / "evil.xml.xml"
    assert plan.target_path.parent == safe_folder


def test_plan_playlist_file_export_flattens_parent_traversal_in_requested_name(tmp_path: Path) -> None:
    """A relative traversal must collapse to a single component inside the safe folder."""
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])
    safe_folder = tmp_path / "safe"

    plan = plan_playlist_file_export(
        software="Traktor",
        recommendation=recommendation,
        safe_folder=safe_folder,
        requested_name="../../outside",
        variant_name=None,
    )

    assert plan.target_name == "outside"
    assert plan.target_path == safe_folder / "outside.nml"
    assert plan.target_path.parent == safe_folder
    assert safe_folder in plan.target_path.parents


def test_plan_playlist_file_export_flattens_nested_subdirectory_in_requested_name(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])
    safe_folder = tmp_path / "safe"

    plan = plan_playlist_file_export(
        software="VirtualDJ",
        recommendation=recommendation,
        safe_folder=safe_folder,
        requested_name="nested/deeper/set",
        variant_name=None,
    )

    assert plan.target_name == "set"
    assert plan.target_path == safe_folder / "set.xml"


def test_plan_playlist_file_export_contains_parent_traversal_in_variant_name(tmp_path: Path) -> None:
    """The variant fallback is the same write path, so it needs the same containment."""
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])
    safe_folder = tmp_path / "safe"

    plan = plan_playlist_file_export(
        software="Rekordbox",
        recommendation=recommendation,
        safe_folder=safe_folder,
        requested_name=None,
        variant_name="../../outside",
    )

    assert plan.target_name == "outside"
    assert plan.target_path == safe_folder / "outside.xml"


@pytest.mark.parametrize("degenerate", [".", "..", "   ", "/", "../..", "nested/.."])
def test_plan_playlist_file_export_rejects_name_that_is_not_a_file_component(tmp_path: Path, degenerate: str) -> None:
    """A name with no usable file component is rejected instead of resolved to the folder itself."""
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    with pytest.raises(ValueError, match="single file name"):
        plan_playlist_file_export(
            software="Rekordbox",
            recommendation=recommendation,
            safe_folder=tmp_path / "safe",
            requested_name=degenerate,
            variant_name=None,
        )


def test_plan_playlist_file_export_rejects_requested_name_with_null_byte(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    with pytest.raises(ValueError, match="single file name"):
        plan_playlist_file_export(
            software="Rekordbox",
            recommendation=recommendation,
            safe_folder=tmp_path / "safe",
            requested_name="evil\x00.xml",
            variant_name=None,
        )
