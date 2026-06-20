"""Playlist export and explainability helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xfinaudio.exporting.explainability import (
        PlaylistExplanation,
        TransitionExplanation,
        build_playlist_explanation,
    )
    from xfinaudio.exporting.playlist_exporters import (
        ExporterRegistry,
        PlaylistExporter,
        default_exporter_registry,
        export_playlist_csv,
        export_playlist_json,
        export_playlist_m3u,
        export_quality_report_json,
        write_playlist_csv,
        write_playlist_json,
        write_playlist_m3u,
    )
    from xfinaudio.exporting.serato_crate import (
        SeratoExportPlan,
        SeratoWriteResult,
        build_serato_crate_bytes,
        plan_serato_crate_export,
        write_serato_crate,
    )
    from xfinaudio.exporting.serato_playlist_exporter import (
        SeratoLibrary,
        SeratoLibraryNotFoundError,
        discover_serato_libraries,
        plan_copilot_variant_serato_playlist_export,
        plan_generated_serato_playlist_export,
        plan_metadata_missing_field_serato_export,
        plan_metadata_status_serato_export,
        plan_serato_playlist_export,
        select_serato_library_for_tracks,
        to_serato_crate_path,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "ExporterRegistry": ("xfinaudio.exporting.playlist_exporters", "ExporterRegistry"),
    "PlaylistExplanation": ("xfinaudio.exporting.explainability", "PlaylistExplanation"),
    "PlaylistExporter": ("xfinaudio.exporting.playlist_exporters", "PlaylistExporter"),
    "SeratoExportPlan": ("xfinaudio.exporting.serato_crate", "SeratoExportPlan"),
    "SeratoLibrary": ("xfinaudio.exporting.serato_playlist_exporter", "SeratoLibrary"),
    "SeratoLibraryNotFoundError": ("xfinaudio.exporting.serato_playlist_exporter", "SeratoLibraryNotFoundError"),
    "SeratoWriteResult": ("xfinaudio.exporting.serato_crate", "SeratoWriteResult"),
    "TransitionExplanation": ("xfinaudio.exporting.explainability", "TransitionExplanation"),
    "build_playlist_explanation": ("xfinaudio.exporting.explainability", "build_playlist_explanation"),
    "build_serato_crate_bytes": ("xfinaudio.exporting.serato_crate", "build_serato_crate_bytes"),
    "default_exporter_registry": ("xfinaudio.exporting.playlist_exporters", "default_exporter_registry"),
    "discover_serato_libraries": ("xfinaudio.exporting.serato_playlist_exporter", "discover_serato_libraries"),
    "export_playlist_csv": ("xfinaudio.exporting.playlist_exporters", "export_playlist_csv"),
    "export_playlist_json": ("xfinaudio.exporting.playlist_exporters", "export_playlist_json"),
    "export_playlist_m3u": ("xfinaudio.exporting.playlist_exporters", "export_playlist_m3u"),
    "export_quality_report_json": ("xfinaudio.exporting.playlist_exporters", "export_quality_report_json"),
    "plan_copilot_variant_serato_playlist_export": (
        "xfinaudio.exporting.serato_playlist_exporter",
        "plan_copilot_variant_serato_playlist_export",
    ),
    "plan_generated_serato_playlist_export": (
        "xfinaudio.exporting.serato_playlist_exporter",
        "plan_generated_serato_playlist_export",
    ),
    "plan_metadata_missing_field_serato_export": (
        "xfinaudio.exporting.serato_playlist_exporter",
        "plan_metadata_missing_field_serato_export",
    ),
    "plan_metadata_status_serato_export": (
        "xfinaudio.exporting.serato_playlist_exporter",
        "plan_metadata_status_serato_export",
    ),
    "plan_serato_crate_export": ("xfinaudio.exporting.serato_crate", "plan_serato_crate_export"),
    "plan_serato_playlist_export": ("xfinaudio.exporting.serato_playlist_exporter", "plan_serato_playlist_export"),
    "select_serato_library_for_tracks": (
        "xfinaudio.exporting.serato_playlist_exporter",
        "select_serato_library_for_tracks",
    ),
    "to_serato_crate_path": ("xfinaudio.exporting.serato_playlist_exporter", "to_serato_crate_path"),
    "write_playlist_csv": ("xfinaudio.exporting.playlist_exporters", "write_playlist_csv"),
    "write_playlist_json": ("xfinaudio.exporting.playlist_exporters", "write_playlist_json"),
    "write_playlist_m3u": ("xfinaudio.exporting.playlist_exporters", "write_playlist_m3u"),
    "write_serato_crate": ("xfinaudio.exporting.serato_crate", "write_serato_crate"),
}

__all__ = [
    "ExporterRegistry",
    "PlaylistExplanation",
    "PlaylistExporter",
    "SeratoExportPlan",
    "SeratoLibrary",
    "SeratoLibraryNotFoundError",
    "SeratoWriteResult",
    "TransitionExplanation",
    "build_playlist_explanation",
    "build_serato_crate_bytes",
    "default_exporter_registry",
    "discover_serato_libraries",
    "export_playlist_csv",
    "export_playlist_json",
    "export_playlist_m3u",
    "export_quality_report_json",
    "plan_copilot_variant_serato_playlist_export",
    "plan_generated_serato_playlist_export",
    "plan_metadata_missing_field_serato_export",
    "plan_metadata_status_serato_export",
    "plan_serato_crate_export",
    "plan_serato_playlist_export",
    "select_serato_library_for_tracks",
    "to_serato_crate_path",
    "write_playlist_csv",
    "write_playlist_json",
    "write_playlist_m3u",
    "write_serato_crate",
]


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily to avoid package-level dependency cycles."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
