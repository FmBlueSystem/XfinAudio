"""Canonical dependency bundle for extracted desktop export responsibilities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from xfinaudio.application.playlist_file_export import (
        PlaylistFileExportResult,
        PlaylistFileExportWriters,
    )
    from xfinaudio.application.serato_playlist_export import LibraryDiscoverer, SeratoPlaylistExportResult
    from xfinaudio.exporting.export_readiness import ExportGateDecision, ExportGateRequest
    from xfinaudio.exporting.playlist_file_export import PlaylistFileExportPlan
    from xfinaudio.quality.dj_readiness import DjReadinessReport
    from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class PreviewPlaylistFileExportContract(Protocol):
    """Callable contract for previewing a non-Serato playlist file export."""

    def __call__(
        self,
        *,
        software: str,
        recommendation: PlaylistRecommendation,
        safe_folder: Path,
        requested_name: str | None,
        variant_name: str | None,
        generated_at: datetime | None = None,
    ) -> PlaylistFileExportPlan: ...


class ExportPlaylistFileContract(Protocol):
    """Callable contract for writing a confirmed non-Serato playlist file export."""

    def __call__(
        self,
        *,
        software: str,
        recommendation: PlaylistRecommendation,
        safe_folder: Path,
        requested_name: str | None,
        variant_name: str | None,
        generated_at: datetime | None = None,
        writers: PlaylistFileExportWriters | None = None,
    ) -> PlaylistFileExportResult: ...


class ExportSeratoPlaylistContract(Protocol):
    """Callable contract for writing a confirmed Serato crate export."""

    def __call__(
        self,
        *,
        recommendation: PlaylistRecommendation,
        copilot_variant_name: str | None,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
        discover_libraries: LibraryDiscoverer = ...,
    ) -> SeratoPlaylistExportResult: ...


class WriteReadinessSidecarsContract(Protocol):
    """Callable contract for writing DJ readiness sidecars beside a written crate."""

    def __call__(
        self,
        report: DjReadinessReport,
        crate_path: Path,
        *,
        safe_folder: Path | None = None,
    ) -> tuple[Path, Path]: ...


@dataclass(frozen=True)
class ExportDependencies:
    evaluate_export_gate: Callable[[ExportGateRequest], ExportGateDecision]
    preview_playlist_file_export: PreviewPlaylistFileExportContract
    export_playlist_file: ExportPlaylistFileContract
    export_serato_playlist: ExportSeratoPlaylistContract
    discover_serato_libraries: LibraryDiscoverer
    write_readiness_sidecars: WriteReadinessSidecarsContract


class ExportDependencyOwner(Protocol):
    def _export_dependencies(self) -> ExportDependencies: ...


def default_export_dependencies() -> ExportDependencies:
    """Build standalone dependencies without importing the compatibility facade."""
    from xfinaudio.application.playlist_file_export import export_playlist_file, preview_playlist_file_export
    from xfinaudio.application.serato_playlist_export import export_serato_playlist
    from xfinaudio.desktop.serato_recommendation_export import write_readiness_sidecars
    from xfinaudio.exporting.export_readiness import evaluate_export_gate
    from xfinaudio.exporting.serato_playlist_exporter import discover_serato_libraries

    return ExportDependencies(
        evaluate_export_gate=evaluate_export_gate,
        preview_playlist_file_export=preview_playlist_file_export,
        export_playlist_file=export_playlist_file,
        export_serato_playlist=export_serato_playlist,
        discover_serato_libraries=discover_serato_libraries,
        write_readiness_sidecars=write_readiness_sidecars,
    )


def resolve_export_dependencies(owner: ExportDependencyOwner | object) -> ExportDependencies:
    """Use an owner's explicit bundle or the canonical standalone bundle."""
    resolver = getattr(owner, "_export_dependencies", None)
    return resolver() if resolver is not None else default_export_dependencies()
