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
