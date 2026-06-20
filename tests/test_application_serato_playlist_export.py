"""Tests for the application-level Serato playlist export use case."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from xfinaudio.application.serato_playlist_export import (
    export_serato_playlist,
    preview_serato_playlist_export,
)
from xfinaudio.exporting.serato_crate import SeratoExportPlan, SeratoWriteResult
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


def test_preview_serato_playlist_export_returns_plan_without_writing(tmp_path: Path) -> None:
    serato_folder = tmp_path / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])

    result = preview_serato_playlist_export(
        recommendation=recommendation,
        copilot_variant_name=None,
        serato_folder=serato_folder,
        crate_name="Warmup",
        generated_at=datetime(2024, 3, 10, 8, 0, 0),
    )

    assert result.plan.crate_name == "Warmup"
    assert result.plan.target_path == serato_folder / "Subcrates" / "Warmup.crate"
    assert result.library.serato_folder == serato_folder
    assert not result.plan.target_path.exists()


def test_export_serato_playlist_confirms_write_through_injected_writer(tmp_path: Path) -> None:
    serato_folder = tmp_path / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    recommendation = _make_recommendation([str(tmp_path / "track.flac")])
    calls: list[tuple[SeratoExportPlan, bool]] = []

    def write_crate(plan: SeratoExportPlan, *, confirm: bool = False) -> SeratoWriteResult:
        calls.append((plan, confirm))
        return SeratoWriteResult(
            written_path=plan.target_path,
            backup_path=None,
            bytes_written=len(plan.crate_bytes),
            validated=True,
            rollback_available=True,
            rollback_action="delete_created_crate",
        )

    result = export_serato_playlist(
        recommendation=recommendation,
        copilot_variant_name=None,
        serato_folder=serato_folder,
        crate_name="Warmup",
        writer=write_crate,
    )

    assert result.plan.crate_name == "Warmup"
    assert result.write_result.written_path == serato_folder / "Subcrates" / "Warmup.crate"
    assert calls == [(result.plan, True)]
