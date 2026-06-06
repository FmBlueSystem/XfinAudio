"""Tests for ExportCoordinator — pure export state logic extracted from MainWindow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from xfinaudio.desktop.export_coordinator import record_export, write_readiness_sidecars


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
