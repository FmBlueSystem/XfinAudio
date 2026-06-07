"""Pure export coordination logic — no Qt dependencies."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    discover_serato_libraries,
    plan_copilot_variant_serato_playlist_export,
    plan_generated_serato_playlist_export,
    plan_serato_playlist_export,
    select_serato_library_for_tracks,
)
from xfinaudio.quality.dj_readiness import DjReadinessReport, write_dj_readiness_report
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


def plan_serato_export(
    recommendation: PlaylistRecommendation,
    copilot_variant_name: str | None,
    *,
    serato_folder: Path | None = None,
    crate_name: str | None = None,
    generated_at: datetime | None = None,
) -> tuple[Any, SeratoLibrary]:
    """Build a Serato export plan without writing it.

    Selects the appropriate planning strategy based on whether a crate_name or
    copilot_variant_name is provided, falling back to a generated strategy name.
    """
    library = (
        SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
        if serato_folder is not None
        else select_serato_library_for_tracks(
            [track.path for track in recommendation.ordered_tracks],
            discover_serato_libraries(),
        )
    )
    if crate_name is not None:
        plan = plan_serato_playlist_export(crate_name, recommendation, library)
    elif copilot_variant_name is not None:
        plan = plan_copilot_variant_serato_playlist_export(
            copilot_variant_name,
            recommendation,
            library,
            generated_at=generated_at,
        )
    else:
        plan = plan_generated_serato_playlist_export(
            recommendation,
            library,
            generated_at=generated_at,
        )
    return plan, library


def build_serato_export_entry(
    recommendation: PlaylistRecommendation,
    written_path: Path,
    *,
    readiness_json_path: Path | None = None,
    readiness_csv_path: Path | None = None,
) -> dict[str, str]:
    """Build a Serato export receipt dict from a completed export."""
    return {
        "time": datetime.now().strftime("%H:%M:%S"),
        "strategy": recommendation.strategy.name,
        "tracks": str(len(recommendation.ordered_tracks)),
        "path": str(written_path),
        "readiness_json_path": "" if readiness_json_path is None else str(readiness_json_path),
        "readiness_csv_path": "" if readiness_csv_path is None else str(readiness_csv_path),
    }


def record_export(
    history: list[dict],
    entry: dict,
    max_entries: int = 5,
) -> list[dict]:
    """Return a new history list with entry prepended and truncated to max_entries."""
    return [entry, *history][:max_entries]


def write_readiness_sidecars(
    report: DjReadinessReport,
    crate_path: Path,
    *,
    safe_folder: Path | None = None,
) -> tuple[Path, Path]:
    """Write DJ Readiness JSON/CSV sidecars to safe_folder (or next to the crate as fallback)."""
    base = safe_folder if safe_folder is not None else crate_path.parent
    stem = crate_path.stem
    json_path = base / f"{stem}.dj-readiness.json"
    csv_path = base / f"{stem}.dj-readiness.csv"
    return write_dj_readiness_report(report, json_path, csv_path)
