"""Pure export coordination logic — no Qt dependencies."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.quality.dj_readiness import DjReadinessReport, write_dj_readiness_report


def record_export(
    history: list[dict],
    entry: dict,
    max_entries: int = 5,
) -> list[dict]:
    """Return a new history list with entry prepended and truncated to max_entries."""
    return [entry, *history][:max_entries]


def write_readiness_sidecars(report: DjReadinessReport, crate_path: Path) -> tuple[Path, Path]:
    """Write DJ Readiness JSON/CSV sidecars next to a Serato crate path."""
    json_path = crate_path.with_suffix(".dj-readiness.json")
    csv_path = crate_path.with_suffix(".dj-readiness.csv")
    return write_dj_readiness_report(report, json_path, csv_path)
