"""Tests for UI-independent export readiness gate decisions."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import cast

import pytest

from xfinaudio.exporting.export_readiness import ExportGateOperation, ExportGateRequest, evaluate_export_gate


def _request(
    *,
    operation: ExportGateOperation = "export",
    software: str = "Rekordbox",
    has_recommendation: bool = True,
    readiness_status: str | None = "ready",
    safe_folder: Path | None = Path("/safe/export"),
) -> ExportGateRequest:
    return ExportGateRequest(
        operation=operation,
        software=software,
        has_recommendation=has_recommendation,
        readiness_status=readiness_status,
        safe_folder=safe_folder,
    )


@pytest.mark.parametrize("operation", ["preview", "export"])
def test_missing_recommendation_denies_all_operations(operation: str) -> None:
    decision = evaluate_export_gate(
        _request(operation=cast(ExportGateOperation, operation), has_recommendation=False, safe_folder=Path("/safe"))
    )

    assert decision.allowed is False
    assert decision.code == "missing_recommendation"


def test_blocked_readiness_denies_export() -> None:
    decision = evaluate_export_gate(_request(operation="export", readiness_status="blocked"))

    assert decision.allowed is False
    assert decision.code == "blocked_readiness"


def test_blocked_readiness_does_not_deny_preview() -> None:
    decision = evaluate_export_gate(_request(operation="preview", readiness_status="blocked"))

    assert decision.allowed is True
    assert decision.code == "allowed"


@pytest.mark.parametrize("operation", ["preview", "export"])
def test_non_serato_requires_safe_folder(operation: str) -> None:
    decision = evaluate_export_gate(
        _request(operation=cast(ExportGateOperation, operation), software="Rekordbox", safe_folder=None)
    )

    assert decision.allowed is False
    assert decision.code == "missing_safe_folder"


@pytest.mark.parametrize("operation", ["preview", "export"])
def test_serato_does_not_require_safe_folder(operation: str) -> None:
    decision = evaluate_export_gate(
        _request(operation=cast(ExportGateOperation, operation), software="Serato", safe_folder=None)
    )

    assert decision.allowed is True
    assert decision.code == "allowed"


def test_unknown_non_serato_software_is_allowed_past_readiness_when_inputs_exist() -> None:
    decision = evaluate_export_gate(_request(software="MadeUpDJ", safe_folder=Path("/safe")))

    assert decision.allowed is True
    assert decision.code == "allowed"


def test_export_readiness_boundary_does_not_import_desktop_or_pyside() -> None:
    import xfinaudio.exporting.export_readiness as export_readiness

    source = inspect.getsource(export_readiness)

    assert "xfinaudio.desktop" not in source
    assert "PySide6" not in source
