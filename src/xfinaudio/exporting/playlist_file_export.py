"""Pure planning for non-Serato playlist file exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xfinaudio.exporting.export_naming import default_export_filename
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

_PLAYLIST_FILE_EXTENSIONS = {
    "Rekordbox": ".xml",
    "Traktor": ".nml",
    "VirtualDJ": ".xml",
}


@dataclass(frozen=True)
class PlaylistFileExportPlan:
    """Resolved target for a non-Serato playlist file export."""

    software: str
    target_name: str
    target_path: Path
    playlist_name: str


def plan_playlist_file_export(
    *,
    software: str,
    recommendation: PlaylistRecommendation,
    safe_folder: Path,
    requested_name: str | None,
    variant_name: str | None,
    generated_at: datetime | None = None,
) -> PlaylistFileExportPlan:
    """Build a deterministic non-Serato playlist file export plan without writing files."""
    extension = _PLAYLIST_FILE_EXTENSIONS.get(software)
    if extension is None:
        raise ValueError(f"Unknown export software: {software}")

    target_name = (
        requested_name
        or variant_name
        or default_export_filename(
            recommendation,
            generated_at=generated_at,
            suffix=software.lower(),
        )
    )
    return PlaylistFileExportPlan(
        software=software,
        target_name=target_name,
        target_path=safe_folder / f"{target_name}{extension}",
        playlist_name=target_name,
    )
