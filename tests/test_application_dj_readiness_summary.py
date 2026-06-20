from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_application_formats_dj_readiness_summary_through_quality_formatter() -> None:
    from xfinaudio.application.dj_readiness import format_application_dj_readiness_summary

    report = MagicMock()

    with patch(
        "xfinaudio.application.dj_readiness._format_dj_readiness_summary",
        return_value="Ready summary",
    ) as formatter:
        result = format_application_dj_readiness_summary(report)

    formatter.assert_called_once_with(report)
    assert result == "Ready summary"


def test_desktop_uses_application_dj_readiness_summary_formatter() -> None:
    for path in (
        Path("src/xfinaudio/desktop/dj_readiness_controller.py"),
        Path("src/xfinaudio/desktop/prep_copilot.py"),
    ):
        source = path.read_text()
        assert "format_application_dj_readiness_summary" in source
        assert "from xfinaudio.quality.dj_readiness import format_dj_readiness_summary" not in source
