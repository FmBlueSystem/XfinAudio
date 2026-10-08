"""Pure planning for non-Serato playlist file exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xfinaudio.exporting.export_naming import default_export_filename
from xfinaudio.exporting.software import playlist_file_extension
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


@dataclass(frozen=True)
class PlaylistFileExportPlan:
    """Resolved target for a non-Serato playlist file export."""

    software: str
    target_name: str
    target_path: Path
    playlist_name: str


def safe_target_name(value: str) -> str:
    """Reduce a caller-supplied export name to one safe filesystem path component.

    The export name reaches a plain ``write_text`` call, so it must never be able to
    select a directory. Only the final component is kept, which neutralises absolute
    paths, ``..`` traversal, and nested subdirectories; anything that leaves no usable
    component is rejected instead of silently resolving to the folder itself.
    """
    if "\x00" in value:
        raise ValueError("Playlist export name must be a single file name.")
    component = Path(value.strip()).name.strip()
    if component in {"", ".", ".."}:
        raise ValueError("Playlist export name must be a single file name.")
    return component


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
    extension = playlist_file_extension(software)

    chosen_name = (
        requested_name
        or variant_name
        or default_export_filename(
            recommendation,
            generated_at=generated_at,
            suffix=software.lower(),
        )
    )
    target_name = safe_target_name(chosen_name)
    target_path = safe_folder / f"{target_name}{extension}"
    if target_path.parent != safe_folder:
        raise ValueError("Playlist export name must resolve inside the export folder.")
    return PlaylistFileExportPlan(
        software=software,
        target_name=target_name,
        target_path=target_path,
        playlist_name=target_name,
    )
