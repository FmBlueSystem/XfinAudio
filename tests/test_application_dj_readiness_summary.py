from __future__ import annotations

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
