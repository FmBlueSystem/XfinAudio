"""Legacy desktop shell compatibility boundaries.

This module owns temporary MainWindow method grafting used by older desktop
callers and tests. Keep product behavior in controllers/services; this file only
names the compatibility surface while the desktop shell is cleaned up in slices.
"""

from __future__ import annotations

from typing import Any

from xfinaudio.desktop import layout as _layout

LEGACY_LAYOUT_METHODS = {
    "choose_safe_export_folder": _layout.choose_safe_export_folder,
    "_open_settings_dialog": _layout.open_main_settings_dialog,
    "_on_spectral_cohesion_changed": _layout.on_main_spectral_cohesion_changed,
    "set_safe_export_folder": _layout.set_safe_export_folder,
    "export_dj_readiness_report": _layout.export_dj_readiness_report,
    "preview_export": _layout.preview_export,
    "export_recommendation": _layout.export_recommendation,
    "preview_serato_export": _layout.preview_serato_export,
    "export_recommendation_to_serato": _layout.export_recommendation_to_serato,
    "export_metadata_status_to_serato": _layout.export_metadata_status_to_serato,
    "scan_selected_folder": _layout.scan_selected_folder,
    "_begin_scan_state": _layout.begin_main_scan_state,
    "_on_library_selection_changed": _layout.on_main_library_selection_changed,
    "cancel_scan": _layout.cancel_scan,
    "show_tracks": _layout.show_tracks,
    "generate_prep_copilot": _layout.generate_prep_copilot,
    "_apply_prep_copilot_item": _layout.apply_prep_copilot_item,
    "apply_selected_prep_copilot_variant": _layout.apply_selected_prep_copilot_variant,
    "recommend_playlist": _layout.recommend_playlist,
    "_begin_recommendation_state": _layout.begin_main_recommendation_state,
    "_end_recommendation_state": _layout.end_main_recommendation_state,
    "_start_recommendation_worker": _layout.start_main_recommendation_worker,
    "_finish_recommendation": _layout.finish_main_recommendation,
    "_fail_recommendation": _layout.fail_main_recommendation,
    "_populate_dj_readiness_table": _layout.populate_main_dj_readiness_table,
    "_on_recommend_requested": _layout.on_main_recommend_requested,
    "_on_copilot_variant_applied": _layout.on_main_copilot_variant_applied,
    "_format_safe_export_folder_label": _layout.format_main_safe_export_folder_label,
    "choose_folder": _layout.choose_folder,
    "set_selected_folder": _layout.set_selected_folder,
    "_persist_last_scan_folder": _layout.persist_main_last_scan_folder,
    "_populate_track_table": _layout.populate_main_track_table,
    "_apply_song_filter": _layout.apply_main_window_song_filter,
    "_selected_metadata_status_filter": _layout.selected_main_metadata_status_filter,
    "_selected_missing_metadata_filter": _layout.selected_main_missing_metadata_filter,
    "_metadata_status_records": _layout.metadata_main_status_records,
    "_metadata_missing_field_records": _layout.metadata_main_missing_field_records,
    "restore_persisted_tracks": _layout.restore_main_tracks,
    "_start_spectral_completion_worker": _layout.start_main_spectral_completion_worker,
    "_cancel_spectral_completion_worker": _layout.cancel_main_spectral_completion_worker,
    "_on_spectral_progress_updated": _layout.on_main_spectral_progress_updated,
    "_on_spectral_profile_ready": _layout.on_main_spectral_profile_ready,
    "_on_spectral_completion_finished": _layout.on_main_spectral_completion_finished,
    "_clear_scan_dependent_state": _layout.clear_main_scan_dependent_state_via_controller,
    "_refresh_idle_action_state": _layout.refresh_main_idle_action_state,
}


LEGACY_APP_STATE_WRITE_ATTRIBUTES = frozenset(
    {
        "workflow_service",
        "current_scan_cancellation_token",
        "selected_folder",
        "scanned_records",
        "_records_by_path",
        "last_recommendation",
        "last_playlist_explanation",
        "last_quality_report",
        "last_dj_readiness_report",
        "last_prep_copilot_plan",
        "applied_prep_copilot_variant_name",
        "serato_export_history",
        "excluded_paths",
        "locked_paths",
        "playlist_removed_paths",
    }
)


def try_set_legacy_app_state_attribute(target: Any, name: str, value: object) -> bool:
    """Set legacy AppState-backed MainWindow attributes when the shell owns state."""
    state = target.__dict__.get("_state")
    if state is None or name not in LEGACY_APP_STATE_WRITE_ATTRIBUTES:
        return False

    if name == "_records_by_path":
        state.records_by_path = value
    elif name == "applied_prep_copilot_variant_name":
        state.applied_variant_name = value
    elif name == "workflow_service":
        state.workflow_service = value
        if hasattr(target, "_scan_service"):
            target._scan_service.workflow_service = value
        if hasattr(target, "_recommendation_service"):
            target._recommendation_service.workflow_service = value
    elif name == "current_scan_cancellation_token":
        state.current_scan_cancellation_token = value
        if hasattr(target, "_scan_service"):
            target._scan_service.current_scan_cancellation_token = value
    else:
        setattr(state, name, value)
    return True


_MISSING = object()


def try_get_legacy_app_state_attribute(target: Any, name: str) -> object:
    """Return a legacy MainWindow read value, or `_MISSING` when unsupported."""
    delegated = {
        "undo": lambda: target._undo_toolbar.undo,
        "redo": lambda: target._undo_toolbar.redo,
        "_on_track_remove_requested": lambda: target._library_controller.on_track_remove_requested,
    }
    if name in delegated and "_undo_toolbar" in target.__dict__:
        return delegated[name]()
    if name.startswith("_") and name != "_records_by_path":
        raise AttributeError(name)

    state = target.__dict__.get("_state")
    if state is None or name not in LEGACY_APP_STATE_WRITE_ATTRIBUTES:
        return _MISSING

    if name == "_records_by_path":
        return state.records_by_path
    if name == "applied_prep_copilot_variant_name":
        return state.applied_variant_name
    if name == "current_scan_cancellation_token" and hasattr(target, "_scan_service"):
        state.current_scan_cancellation_token = target._scan_service.current_scan_cancellation_token
    return getattr(state, name)


def is_missing_legacy_attribute(value: object) -> bool:
    """Return whether a legacy read helper result means unsupported attribute."""
    return value is _MISSING


def install_legacy_layout_methods(target_class: type) -> None:
    """Install legacy layout-backed methods on a MainWindow-compatible class."""
    for name, method in LEGACY_LAYOUT_METHODS.items():
        setattr(target_class, name, method)
