"""Application workflow services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xfinaudio.application.dj_readiness import (
        build_application_dj_readiness_report,
        format_application_dj_readiness_summary,
        write_application_dj_readiness_report,
    )
    from xfinaudio.application.playlist_workflow import (
        PlaylistWorkflowService,
        RecommendationWorkflowResult,
        ScanService,
        ScanWorkflowResult,
    )
    from xfinaudio.application.prep_copilot import (
        PrepCopilotVariantApplicationResult,
        PrepCopilotVariantLike,
        build_prep_copilot_variant_application,
    )
    from xfinaudio.application.recommendation_candidates import plan_recommendation_candidates
    from xfinaudio.application.saved_playlists import SavedPlaylistExport, SavedPlaylistService
    from xfinaudio.application.serato_metadata_export import (
        SeratoMetadataCrateWriter,
        SeratoMetadataExportResult,
        export_metadata_status_serato_worklist,
        export_missing_field_serato_worklist,
    )
    from xfinaudio.application.serato_playlist_export import (
        SeratoCrateWriter,
        SeratoPlaylistExportPreview,
        SeratoPlaylistExportResult,
        export_serato_playlist,
        preview_serato_playlist_export,
    )
    from xfinaudio.application.spectral_profile_display import format_application_spectral_color
    from xfinaudio.application.strategy_catalog import (
        StrategyCatalogEntry,
        describe_strategy,
        list_strategy_catalog,
    )
    from xfinaudio.application.vertical_playlist_flow import (
        PlaylistWorkflow,
        PlaylistWorkflowRecommender,
        PlaylistWorkflowScanner,
        RecommendationSaver,
        RecommendationWorkflowResultLike,
        SavedPlaylistApplicationExporter,
        SavedPlaylistExportBuilder,
        SavedPlaylistStore,
        ScanWorkflowResultLike,
        VerticalPlaylistFlow,
        VerticalPlaylistFlowResult,
        VerticalSavedPlaylistExportResult,
        VerticalScanRecommendationResult,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "StrategyCatalogEntry": ("xfinaudio.application.strategy_catalog", "StrategyCatalogEntry"),
    "describe_strategy": ("xfinaudio.application.strategy_catalog", "describe_strategy"),
    "list_strategy_catalog": ("xfinaudio.application.strategy_catalog", "list_strategy_catalog"),
    "SeratoMetadataCrateWriter": ("xfinaudio.application.serato_metadata_export", "SeratoMetadataCrateWriter"),
    "SeratoMetadataExportResult": (
        "xfinaudio.application.serato_metadata_export",
        "SeratoMetadataExportResult",
    ),
    "export_metadata_status_serato_worklist": (
        "xfinaudio.application.serato_metadata_export",
        "export_metadata_status_serato_worklist",
    ),
    "export_missing_field_serato_worklist": (
        "xfinaudio.application.serato_metadata_export",
        "export_missing_field_serato_worklist",
    ),
    "SeratoCrateWriter": ("xfinaudio.application.serato_playlist_export", "SeratoCrateWriter"),
    "SeratoPlaylistExportPreview": (
        "xfinaudio.application.serato_playlist_export",
        "SeratoPlaylistExportPreview",
    ),
    "SeratoPlaylistExportResult": (
        "xfinaudio.application.serato_playlist_export",
        "SeratoPlaylistExportResult",
    ),
    "export_serato_playlist": ("xfinaudio.application.serato_playlist_export", "export_serato_playlist"),
    "preview_serato_playlist_export": (
        "xfinaudio.application.serato_playlist_export",
        "preview_serato_playlist_export",
    ),
    "format_application_spectral_color": (
        "xfinaudio.application.spectral_profile_display",
        "format_application_spectral_color",
    ),
    "PrepCopilotVariantApplicationResult": (
        "xfinaudio.application.prep_copilot",
        "PrepCopilotVariantApplicationResult",
    ),
    "PrepCopilotVariantLike": ("xfinaudio.application.prep_copilot", "PrepCopilotVariantLike"),
    "build_prep_copilot_variant_application": (
        "xfinaudio.application.prep_copilot",
        "build_prep_copilot_variant_application",
    ),
    "build_application_dj_readiness_report": (
        "xfinaudio.application.dj_readiness",
        "build_application_dj_readiness_report",
    ),
    "format_application_dj_readiness_summary": (
        "xfinaudio.application.dj_readiness",
        "format_application_dj_readiness_summary",
    ),
    "write_application_dj_readiness_report": (
        "xfinaudio.application.dj_readiness",
        "write_application_dj_readiness_report",
    ),
    "plan_recommendation_candidates": (
        "xfinaudio.application.recommendation_candidates",
        "plan_recommendation_candidates",
    ),
    "PlaylistWorkflowService": ("xfinaudio.application.playlist_workflow", "PlaylistWorkflowService"),
    "PlaylistWorkflow": ("xfinaudio.application.vertical_playlist_flow", "PlaylistWorkflow"),
    "PlaylistWorkflowRecommender": ("xfinaudio.application.vertical_playlist_flow", "PlaylistWorkflowRecommender"),
    "PlaylistWorkflowScanner": ("xfinaudio.application.vertical_playlist_flow", "PlaylistWorkflowScanner"),
    "RecommendationWorkflowResult": ("xfinaudio.application.playlist_workflow", "RecommendationWorkflowResult"),
    "RecommendationSaver": ("xfinaudio.application.vertical_playlist_flow", "RecommendationSaver"),
    "RecommendationWorkflowResultLike": (
        "xfinaudio.application.vertical_playlist_flow",
        "RecommendationWorkflowResultLike",
    ),
    "SavedPlaylistExport": ("xfinaudio.application.saved_playlists", "SavedPlaylistExport"),
    "SavedPlaylistApplicationExporter": (
        "xfinaudio.application.vertical_playlist_flow",
        "SavedPlaylistApplicationExporter",
    ),
    "SavedPlaylistExportBuilder": ("xfinaudio.application.vertical_playlist_flow", "SavedPlaylistExportBuilder"),
    "SavedPlaylistService": ("xfinaudio.application.saved_playlists", "SavedPlaylistService"),
    "SavedPlaylistStore": ("xfinaudio.application.vertical_playlist_flow", "SavedPlaylistStore"),
    "ScanService": ("xfinaudio.application.playlist_workflow", "ScanService"),
    "ScanWorkflowResult": ("xfinaudio.application.playlist_workflow", "ScanWorkflowResult"),
    "ScanWorkflowResultLike": ("xfinaudio.application.vertical_playlist_flow", "ScanWorkflowResultLike"),
    "VerticalPlaylistFlow": ("xfinaudio.application.vertical_playlist_flow", "VerticalPlaylistFlow"),
    "VerticalPlaylistFlowResult": ("xfinaudio.application.vertical_playlist_flow", "VerticalPlaylistFlowResult"),
    "VerticalSavedPlaylistExportResult": (
        "xfinaudio.application.vertical_playlist_flow",
        "VerticalSavedPlaylistExportResult",
    ),
    "VerticalScanRecommendationResult": (
        "xfinaudio.application.vertical_playlist_flow",
        "VerticalScanRecommendationResult",
    ),
}

__all__ = [
    "StrategyCatalogEntry",
    "describe_strategy",
    "list_strategy_catalog",
    "SeratoMetadataExportResult",
    "export_metadata_status_serato_worklist",
    "export_missing_field_serato_worklist",
    "SeratoMetadataCrateWriter",
    "SeratoCrateWriter",
    "SeratoPlaylistExportPreview",
    "SeratoPlaylistExportResult",
    "export_serato_playlist",
    "preview_serato_playlist_export",
    "format_application_spectral_color",
    "PrepCopilotVariantApplicationResult",
    "PrepCopilotVariantLike",
    "build_prep_copilot_variant_application",
    "build_application_dj_readiness_report",
    "format_application_dj_readiness_summary",
    "write_application_dj_readiness_report",
    "plan_recommendation_candidates",
    "PlaylistWorkflowService",
    "PlaylistWorkflow",
    "PlaylistWorkflowRecommender",
    "PlaylistWorkflowScanner",
    "RecommendationWorkflowResult",
    "RecommendationSaver",
    "RecommendationWorkflowResultLike",
    "SavedPlaylistExport",
    "SavedPlaylistApplicationExporter",
    "SavedPlaylistExportBuilder",
    "SavedPlaylistService",
    "SavedPlaylistStore",
    "ScanService",
    "ScanWorkflowResult",
    "ScanWorkflowResultLike",
    "VerticalPlaylistFlow",
    "VerticalPlaylistFlowResult",
    "VerticalSavedPlaylistExportResult",
    "VerticalScanRecommendationResult",
]


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily to keep application submodule imports isolated."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
