"""Tests for ExportCoordinator — pure export state logic extracted from MainWindow."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from xfinaudio.desktop.export_coordinator import plan_serato_export, record_export, write_readiness_sidecars
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


def test_record_export_prepends_entry():
    history: list[dict] = []
    entry = {"time": "10:00", "path": "/out/a.crate"}
    result = record_export(history, entry)
    assert result == [entry]


def test_record_export_newest_first():
    old = {"time": "09:00", "path": "/out/old.crate"}
    new = {"time": "10:00", "path": "/out/new.crate"}
    result = record_export([old], new)
    assert result[0] == new
    assert result[1] == old


def test_record_export_truncates_to_max_entries():
    history = [{"path": str(i)} for i in range(4)]
    entry = {"path": "new"}
    result = record_export(history, entry, max_entries=5)
    assert len(result) == 5
    assert result[0] == entry


def test_record_export_drops_oldest_when_over_limit():
    history = [{"path": str(i)} for i in range(5)]
    entry = {"path": "newest"}
    result = record_export(history, entry, max_entries=5)
    assert len(result) == 5
    assert result[0]["path"] == "newest"
    assert result[-1]["path"] == "3"


def test_record_export_does_not_mutate_input():
    history = [{"path": "a"}]
    original = list(history)
    record_export(history, {"path": "b"})
    assert history == original


def test_write_readiness_sidecars_calls_writer(tmp_path: Path):
    crate_path = tmp_path / "mix.crate"
    report = MagicMock()
    expected_json = crate_path.with_suffix(".dj-readiness.json")
    expected_csv = crate_path.with_suffix(".dj-readiness.csv")

    with patch(
        "xfinaudio.desktop.export_coordinator.write_dj_readiness_report",
        return_value=(expected_json, expected_csv),
    ) as mock_write:
        json_path, csv_path = write_readiness_sidecars(report, crate_path)

    mock_write.assert_called_once_with(report, expected_json, expected_csv)
    assert json_path == expected_json
    assert csv_path == expected_csv


def test_write_readiness_sidecars_derives_paths_from_crate(tmp_path: Path):
    crate_path = tmp_path / "subcrates" / "set.crate"
    report = MagicMock()
    with patch("xfinaudio.desktop.export_coordinator.write_dj_readiness_report", return_value=(Path("a"), Path("b"))):
        write_readiness_sidecars(report, crate_path)


def test_plan_serato_export_uses_crate_name_when_provided(tmp_path: Path) -> None:
    serato_folder = tmp_path / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    track_path = str(tmp_path / "track.flac")
    recommendation = _make_recommendation([track_path])

    plan, library = plan_serato_export(
        recommendation,
        None,
        serato_folder=serato_folder,
        crate_name="My Custom Set",
    )

    assert plan.crate_name == "My Custom Set"
    assert plan.target_path == serato_folder / "Subcrates" / "My Custom Set.crate"
    assert library.serato_folder == serato_folder


def test_plan_serato_export_uses_copilot_variant_when_no_crate_name(tmp_path: Path) -> None:
    serato_folder = tmp_path / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    track_path = str(tmp_path / "track.flac")
    recommendation = _make_recommendation([track_path])
    fixed_dt = datetime(2024, 1, 15, 10, 30, 0)

    plan, library = plan_serato_export(
        recommendation,
        "balanced",
        serato_folder=serato_folder,
        generated_at=fixed_dt,
    )

    assert "balanced" in plan.crate_name.lower() or "Balanced" in plan.crate_name
    assert plan.target_path.suffix == ".crate"
    assert library.serato_folder == serato_folder


def test_plan_serato_export_uses_generated_strategy_name_when_no_variant(tmp_path: Path) -> None:
    serato_folder = tmp_path / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    track_path = str(tmp_path / "track.flac")
    recommendation = _make_recommendation([track_path])
    fixed_dt = datetime(2024, 3, 10, 8, 0, 0)

    plan, library = plan_serato_export(
        recommendation,
        None,
        serato_folder=serato_folder,
        generated_at=fixed_dt,
    )

    assert "20240310" in plan.crate_name
    assert plan.target_path.suffix == ".crate"
    assert library.serato_folder == serato_folder
