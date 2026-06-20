"""Application workflow services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xfinaudio.application.playlist_workflow import (
        PlaylistWorkflowService,
        RecommendationWorkflowResult,
        ScanService,
        ScanWorkflowResult,
    )
    from xfinaudio.application.saved_playlists import SavedPlaylistExport, SavedPlaylistService
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
