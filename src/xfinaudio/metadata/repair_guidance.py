"""Qt translation adapter for the shared read-only repair guidance."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QCoreApplication

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata import repair_guidance_core as core
from xfinaudio.metadata.repair_guidance_core import RepairPriority as RepairPriority


def _tr(text: str) -> str:
    return QCoreApplication.translate("MetadataRepairGuidance", text)


def prioritize_repairs(
    records: Iterable[TrackRecord], *, locked_paths: frozenset[str] = frozenset()
) -> list[RepairPriority]:
    """Locked tracks first, then fewer repairs; stable paths break equal priorities."""
    return core.prioritize_repairs(records, locked_paths=locked_paths, translate=_tr)


def explain_track_gaps(record: TrackRecord) -> str:
    """Describe consequences of absent fields, never propose fabricated tag values."""
    return core.explain_track_gaps(record, translate=_tr)


def repair_plan_text(records: Iterable[TrackRecord], *, locked_paths: frozenset[str] = frozenset()) -> str:
    """Render a bounded, transparent local repair plan, with no file writes."""
    return core.repair_plan_text(records, locked_paths=locked_paths, translate=_tr)
