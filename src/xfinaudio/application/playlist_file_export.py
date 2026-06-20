"""Application use case for non-Serato playlist file exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from xfinaudio.exporting.playlist_file_export import PlaylistFileExportPlan, plan_playlist_file_export
from xfinaudio.exporting.rekordbox_xml import write_rekordbox_playlist_xml
from xfinaudio.exporting.software import playlist_file_extension
from xfinaudio.exporting.traktor_nml import write_traktor_playlist_nml
from xfinaudio.exporting.virtualdj_xml import write_virtualdj_playlist_xml
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class PlaylistFileWriter(Protocol):
    """Callable writer contract for a playlist file export."""

    def __call__(self, recommendation: PlaylistRecommendation, target: Path, *, playlist_name: str) -> Path: ...


@dataclass(frozen=True)
class PlaylistFileExportWriters:
    """Writer dependencies for non-Serato playlist file exports."""

    rekordbox: PlaylistFileWriter = write_rekordbox_playlist_xml
    traktor: PlaylistFileWriter = write_traktor_playlist_nml
    virtualdj: PlaylistFileWriter = write_virtualdj_playlist_xml


@dataclass(frozen=True)
class PlaylistFileExportResult:
    """Application result for a written playlist file export."""

    plan: PlaylistFileExportPlan
    written_path: Path


def preview_playlist_file_export(
    *,
    software: str,
    recommendation: PlaylistRecommendation,
    safe_folder: Path,
    requested_name: str | None,
    variant_name: str | None,
    generated_at: datetime | None = None,
) -> PlaylistFileExportPlan:
    """Return a non-Serato export plan without writing files."""
    return plan_playlist_file_export(
        software=software,
        recommendation=recommendation,
        safe_folder=safe_folder,
        requested_name=requested_name,
        variant_name=variant_name,
        generated_at=generated_at,
    )


def export_playlist_file(
    *,
    software: str,
    recommendation: PlaylistRecommendation,
    safe_folder: Path,
    requested_name: str | None,
    variant_name: str | None,
    generated_at: datetime | None = None,
    writers: PlaylistFileExportWriters | None = None,
) -> PlaylistFileExportResult:
    """Write a non-Serato playlist file through the selected writer."""
    plan = preview_playlist_file_export(
        software=software,
        recommendation=recommendation,
        safe_folder=safe_folder,
        requested_name=requested_name,
        variant_name=variant_name,
        generated_at=generated_at,
    )
    writer_bundle = writers or PlaylistFileExportWriters()
    playlist_file_extension(software)
    writer = {
        "Rekordbox": writer_bundle.rekordbox,
        "Traktor": writer_bundle.traktor,
        "VirtualDJ": writer_bundle.virtualdj,
    }[software]
    written_path = writer(recommendation, plan.target_path, playlist_name=plan.playlist_name)
    return PlaylistFileExportResult(plan=plan, written_path=written_path)


__all__ = [
    "PlaylistFileExportResult",
    "PlaylistFileExportWriters",
    "export_playlist_file",
    "preview_playlist_file_export",
]
