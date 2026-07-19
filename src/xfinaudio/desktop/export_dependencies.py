"""Canonical dependency bundle for extracted desktop export responsibilities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ExportDependencies:
    evaluate_export_gate: Callable[..., Any]
    preview_playlist_file_export: Callable[..., Any]
    export_playlist_file: Callable[..., Any]
    export_serato_playlist: Callable[..., Any]
    discover_serato_libraries: Callable[..., Any]
    write_application_dj_readiness_report: Callable[..., Any]
    write_readiness_sidecars: Callable[..., Any]


class ExportDependencyOwner(Protocol):
    def _export_dependencies(self) -> ExportDependencies: ...


def default_export_dependencies() -> ExportDependencies:
    """Build standalone dependencies without importing the compatibility facade."""
    from xfinaudio.application.dj_readiness import write_application_dj_readiness_report
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
        write_application_dj_readiness_report=write_application_dj_readiness_report,
        write_readiness_sidecars=write_readiness_sidecars,
    )


def resolve_export_dependencies(owner: ExportDependencyOwner | object) -> ExportDependencies:
    """Use an owner's explicit bundle or the canonical standalone bundle."""
    resolver = getattr(owner, "_export_dependencies", None)
    return resolver() if resolver is not None else default_export_dependencies()
