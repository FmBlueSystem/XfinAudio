"""Read-only repair priorities and explanations derived from known metadata."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.metadata_gaps import REQUIRED_GAP_FIELDS


def _identity(text: str) -> str:
    return text


@dataclass(frozen=True)
class RepairPriority:
    path: str
    title: str
    missing_fields: tuple[str, ...]
    locked: bool


def prioritize_repairs(
    records: Iterable[TrackRecord],
    *,
    locked_paths: frozenset[str] = frozenset(),
    translate: Callable[[str], str] = _identity,
) -> list[RepairPriority]:
    """Locked tracks first, then fewer repairs; stable paths break equal priorities."""
    priorities = []
    for record in records:
        missing = tuple(field for field in REQUIRED_GAP_FIELDS if getattr(record, field) is None)
        if missing:
            priorities.append(
                RepairPriority(record.path, record.title or translate("Untitled"), missing, record.path in locked_paths)
            )
    return sorted(priorities, key=lambda item: (not item.locked, len(item.missing_fields), item.path))


def explain_track_gaps(record: TrackRecord, *, translate: Callable[[str], str] = _identity) -> str:
    """Describe consequences of absent fields, never propose fabricated tag values."""
    reasons = {
        "bpm": translate("BPM is missing: tempo compatibility cannot be checked."),
        "camelot_key": translate("Key is missing: harmonic compatibility cannot be checked."),
        "energy_level": translate("Energy is missing: the energy progression cannot be checked."),
    }
    lines = [reasons[field] for field in REQUIRED_GAP_FIELDS if getattr(record, field) is None]
    if not lines:
        return translate("No required metadata gaps. Release year is informational only.")
    lines.append(
        translate("Values are not inferred. Correct tags from a verified source in your tag editor, then rescan.")
    )
    return "\n".join(lines)


def repair_plan_text(
    records: Iterable[TrackRecord],
    *,
    locked_paths: frozenset[str] = frozenset(),
    translate: Callable[[str], str] = _identity,
) -> str:
    """Render a bounded, transparent local repair plan, with no file writes."""
    plan = prioritize_repairs(records, locked_paths=locked_paths, translate=translate)
    lines = [translate("Local repair assistant · read-only; no tags are written")]
    if not plan:
        lines.append(translate("No required metadata gaps found."))
        return "\n".join(lines)
    lines.append(
        translate("Priority: locked tracks first, then tracks needing fewer field repairs. No values are inferred.")
    )
    labels = {"bpm": translate("BPM"), "camelot_key": translate("Key"), "energy_level": translate("Energy")}
    for index, item in enumerate(plan[:10], 1):
        missing = ", ".join(labels[field] for field in item.missing_fields)
        lock = translate(" [locked]") if item.locked else ""
        lines.append(f"{index}. {item.title}{lock}: {missing}")
    if len(plan) > 10:
        lines.append(translate("{0} more tracks are available in the repair checklist.").format(len(plan) - 10))
    return "\n".join(lines)
