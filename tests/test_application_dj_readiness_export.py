from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_application_writes_dj_readiness_report_through_quality_writer() -> None:
    from xfinaudio.application.dj_readiness import write_application_dj_readiness_report

    report = MagicMock()
    json_path = Path("report.json")
    csv_path = Path("report.csv")

    with patch(
        "xfinaudio.application.dj_readiness._write_dj_readiness_report",
        return_value=(json_path, csv_path),
    ) as writer:
        result = write_application_dj_readiness_report(report, json_path, csv_path)

    writer.assert_called_once_with(report, json_path, csv_path)
    assert result == (json_path, csv_path)


def test_desktop_exports_use_application_dj_readiness_writer() -> None:
    for path in (Path("src/xfinaudio/desktop/export_actions.py"), Path("src/xfinaudio/desktop/export_coordinator.py")):
        source = path.read_text()
        assert "from xfinaudio.application.dj_readiness import write_application_dj_readiness_report" in source
        assert "from xfinaudio.quality.dj_readiness import write_dj_readiness_report" not in source
