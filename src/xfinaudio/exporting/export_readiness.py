"""UI-independent export readiness gate decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ExportGateOperation = Literal["preview", "export"]
ExportGateCode = Literal["allowed", "missing_recommendation", "blocked_readiness", "missing_safe_folder"]


@dataclass(frozen=True)
class ExportGateRequest:
    """Plain inputs required to decide whether export planning may continue."""

    operation: ExportGateOperation
    software: str
    has_recommendation: bool
    readiness_status: str | None
    safe_folder: Path | None


@dataclass(frozen=True)
class ExportGateDecision:
    """Structured export gate result consumed by UI or application callers."""

    allowed: bool
    code: ExportGateCode


def evaluate_export_gate(request: ExportGateRequest) -> ExportGateDecision:
    """Return the deterministic gate decision for an export request."""
    if not request.has_recommendation:
        return ExportGateDecision(allowed=False, code="missing_recommendation")
    if request.operation == "export" and request.readiness_status == "blocked":
        return ExportGateDecision(allowed=False, code="blocked_readiness")
    if request.software != "Serato" and request.safe_folder is None:
        return ExportGateDecision(allowed=False, code="missing_safe_folder")
    return ExportGateDecision(allowed=True, code="allowed")


__all__ = [
    "ExportGateCode",
    "ExportGateDecision",
    "ExportGateOperation",
    "ExportGateRequest",
    "evaluate_export_gate",
]
