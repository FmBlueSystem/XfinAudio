"""Read-only repair priorities and explanations derived from known metadata."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.metadata_gaps import REQUIRED_GAP_FIELDS


def _tr(text: str) -> str:
    return QCoreApplication.translate("MetadataRepairGuidance", text)


@dataclass(frozen=True)
class RepairPriority:
    path: str
    title: str
    missing_fields: tuple[str, ...]
    locked: bool


def prioritize_repairs(
    records: Iterable[TrackRecord], *, locked_paths: frozenset[str] = frozenset()
) -> list[RepairPriority]:
    """Locked tracks first, then fewer repairs; stable paths break equal priorities."""
    priorities = []
    for record in records:
        missing = tuple(field for field in REQUIRED_GAP_FIELDS if getattr(record, field) is None)
        if missing:
            priorities.append(
                RepairPriority(record.path, record.title or _tr("Untitled"), missing, record.path in locked_paths)
            )
    return sorted(priorities, key=lambda item: (not item.locked, len(item.missing_fields), item.path))


def explain_track_gaps(record: TrackRecord) -> str:
    """Describe consequences of absent fields, never propose fabricated tag values."""
    reasons = {
        "bpm": _tr("BPM is missing: tempo compatibility cannot be checked."),
        "camelot_key": _tr("Key is missing: harmonic compatibility cannot be checked."),
        "energy_level": _tr("Energy is missing: the energy progression cannot be checked."),
    }
    lines = [reasons[field] for field in REQUIRED_GAP_FIELDS if getattr(record, field) is None]
    if not lines:
        return _tr("No required metadata gaps. Release year is informational only.")
    lines.append(_tr("Values are not inferred. Correct tags from a verified source in your tag editor, then rescan."))
    return "\n".join(lines)


def repair_plan_text(records: Iterable[TrackRecord], *, locked_paths: frozenset[str] = frozenset()) -> str:
    """Render a bounded, transparent local repair plan, with no file writes."""
    plan = prioritize_repairs(records, locked_paths=locked_paths)
    lines = [_tr("Local repair assistant · read-only; no tags are written")]
    if not plan:
        lines.append(_tr("No required metadata gaps found."))
        return "\n".join(lines)
    lines.append(_tr("Priority: locked tracks first, then tracks needing fewer field repairs. No values are inferred."))
    labels = {"bpm": _tr("BPM"), "camelot_key": _tr("Key"), "energy_level": _tr("Energy")}
    for index, item in enumerate(plan[:10], 1):
        missing = ", ".join(labels[field] for field in item.missing_fields)
        lock = _tr(" [locked]") if item.locked else ""
        lines.append(f"{index}. {item.title}{lock}: {missing}")
    if len(plan) > 10:
        lines.append(_tr("{0} more tracks are available in the repair checklist.").format(len(plan) - 10))
    return "\n".join(lines)
