"""Application use case for Serato playlist crate exports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from xfinaudio.exporting.serato_crate import SeratoExportPlan, SeratoWriteResult, write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    discover_serato_libraries,
    plan_copilot_variant_serato_playlist_export,
    plan_generated_serato_playlist_export,
    plan_serato_playlist_export,
    select_serato_library_for_tracks,
)
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class SeratoCrateWriter(Protocol):
    """Callable writer contract for confirmed Serato crate exports."""

    def __call__(self, plan: SeratoExportPlan, *, confirm: bool = False) -> SeratoWriteResult: ...


@dataclass(frozen=True)
class SeratoPlaylistExportPreview:
    """Application preview result for a Serato playlist export."""

    plan: SeratoExportPlan
    library: SeratoLibrary


@dataclass(frozen=True)
class SeratoPlaylistExportResult:
    """Application result for a confirmed Serato playlist export."""

    plan: SeratoExportPlan
    library: SeratoLibrary
    write_result: SeratoWriteResult


LibraryDiscoverer = Callable[[], list[SeratoLibrary]]


def preview_serato_playlist_export(
    *,
    recommendation: PlaylistRecommendation,
    copilot_variant_name: str | None,
    serato_folder: Path | None = None,
    crate_name: str | None = None,
    generated_at: datetime | None = None,
    discover_libraries: LibraryDiscoverer = discover_serato_libraries,
) -> SeratoPlaylistExportPreview:
    """Build a Serato playlist export plan without writing files."""
    library = (
        SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
        if serato_folder is not None
        else select_serato_library_for_tracks(
            [track.path for track in recommendation.ordered_tracks],
            discover_libraries(),
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
    return SeratoPlaylistExportPreview(plan=plan, library=library)


def export_serato_playlist(
    *,
    recommendation: PlaylistRecommendation,
    copilot_variant_name: str | None,
    serato_folder: Path | None = None,
    crate_name: str | None = None,
    generated_at: datetime | None = None,
    writer: SeratoCrateWriter = write_serato_crate,
    discover_libraries: LibraryDiscoverer = discover_serato_libraries,
) -> SeratoPlaylistExportResult:
    """Write a confirmed Serato crate through the selected writer."""
    preview = preview_serato_playlist_export(
        recommendation=recommendation,
        copilot_variant_name=copilot_variant_name,
        serato_folder=serato_folder,
        crate_name=crate_name,
        generated_at=generated_at,
        discover_libraries=discover_libraries,
    )
    write_result = writer(preview.plan, confirm=True)
    return SeratoPlaylistExportResult(
        plan=preview.plan,
        library=preview.library,
        write_result=write_result,
    )


__all__ = [
    "SeratoCrateWriter",
    "SeratoPlaylistExportPreview",
    "SeratoPlaylistExportResult",
    "export_serato_playlist",
    "preview_serato_playlist_export",
]
