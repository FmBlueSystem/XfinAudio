"""Tests for the application-level playlist file export use case."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from xfinaudio.application.playlist_file_export import (
    PlaylistFileExportWriters,
    export_playlist_file,
    preview_playlist_file_export,
)
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


def test_preview_playlist_file_export_returns_plan_without_writing(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    plan = preview_playlist_file_export(
        software="VirtualDJ",
        recommendation=recommendation,
        safe_folder=tmp_path,
        requested_name=None,
        variant_name=None,
        generated_at=datetime(2024, 3, 10, 8, 0, 0),
    )

    assert plan.software == "VirtualDJ"
    assert plan.playlist_name == "20240310_080000_build_virtualdj_1_track"
    assert plan.target_path == tmp_path / "20240310_080000_build_virtualdj_1_track.xml"
    assert not plan.target_path.exists()


def test_export_playlist_file_dispatches_registered_writer(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])
    calls: list[tuple[PlaylistRecommendation, Path, str]] = []

    def write_virtualdj(recommendation: PlaylistRecommendation, target: Path, *, playlist_name: str) -> Path:
        calls.append((recommendation, target, playlist_name))
        return target

    result = export_playlist_file(
        software="VirtualDJ",
        recommendation=recommendation,
        safe_folder=tmp_path,
        requested_name="Warmup",
        variant_name=None,
        writers=PlaylistFileExportWriters(virtualdj=write_virtualdj),
    )

    assert result.plan.target_path == tmp_path / "Warmup.xml"
    assert result.written_path == tmp_path / "Warmup.xml"
    assert calls == [(recommendation, tmp_path / "Warmup.xml", "Warmup")]


def test_export_playlist_file_rejects_unknown_software(tmp_path: Path) -> None:
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    with pytest.raises(ValueError, match="Unknown export software: Ableton"):
        export_playlist_file(
            software="Ableton",
            recommendation=recommendation,
            safe_folder=tmp_path,
            requested_name=None,
            variant_name=None,
        )
