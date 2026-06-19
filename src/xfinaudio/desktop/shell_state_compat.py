"""Legacy MainWindow AppState read/write compatibility surface."""

from __future__ import annotations

from typing import Any

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
