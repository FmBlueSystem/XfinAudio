"""Application use case for Serato metadata worklist crate exports."""

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
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    select_serato_library_for_tracks,
)
from xfinaudio.library.models import MetadataStatus, TrackRecord


class SeratoMetadataCrateWriter(Protocol):
    """Callable writer contract for confirmed Serato metadata crate exports."""

    def __call__(self, plan: SeratoExportPlan, *, confirm: bool = False) -> SeratoWriteResult: ...


@dataclass(frozen=True)
class SeratoMetadataExportResult:
    """Application result for a confirmed Serato metadata worklist export."""

    plan: SeratoExportPlan
    library: SeratoLibrary
    write_result: SeratoWriteResult


LibraryDiscoverer = Callable[[], list[SeratoLibrary]]


def _select_library_for_records(
    records: list[TrackRecord] | tuple[TrackRecord, ...],
    *,
    serato_folder: Path | None,
    discover_libraries: LibraryDiscoverer,
) -> SeratoLibrary:
    if serato_folder is not None:
        return SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
    return select_serato_library_for_tracks(
        [record.path for record in records],
        discover_libraries(),
    )


def export_metadata_status_serato_worklist(
    *,
    records: list[TrackRecord] | tuple[TrackRecord, ...],
    status: MetadataStatus,
    serato_folder: Path | None = None,
    generated_at: datetime | None = None,
    writer: SeratoMetadataCrateWriter = write_serato_crate,
    discover_libraries: LibraryDiscoverer = discover_serato_libraries,
) -> SeratoMetadataExportResult:
    """Write a confirmed Serato crate for a complete/incomplete metadata worklist."""
    library = _select_library_for_records(records, serato_folder=serato_folder, discover_libraries=discover_libraries)
    plan = plan_metadata_status_serato_export(records, status, library, generated_at=generated_at)
    write_result = writer(plan, confirm=True)
    return SeratoMetadataExportResult(plan=plan, library=library, write_result=write_result)


def export_missing_field_serato_worklist(
    *,
    records: list[TrackRecord] | tuple[TrackRecord, ...],
    missing_field: str,
    serato_folder: Path | None = None,
    generated_at: datetime | None = None,
    writer: SeratoMetadataCrateWriter = write_serato_crate,
    discover_libraries: LibraryDiscoverer = discover_serato_libraries,
) -> SeratoMetadataExportResult:
    """Write a confirmed Serato crate for a missing metadata field worklist."""
    library = _select_library_for_records(records, serato_folder=serato_folder, discover_libraries=discover_libraries)
    plan = plan_metadata_missing_field_serato_export(records, missing_field, library, generated_at=generated_at)
    write_result = writer(plan, confirm=True)
    return SeratoMetadataExportResult(plan=plan, library=library, write_result=write_result)


__all__ = [
    "SeratoMetadataCrateWriter",
    "SeratoMetadataExportResult",
    "export_metadata_status_serato_worklist",
    "export_missing_field_serato_worklist",
]
