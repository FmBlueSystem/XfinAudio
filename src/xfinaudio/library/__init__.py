"""Library scanning and persistence APIs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xfinaudio.library.models import TrackRecord
    from xfinaudio.library.scan_planning import plan_supported_audio_paths
    from xfinaudio.library.scan_service import MetadataScanService, scan_folder
    from xfinaudio.library.track_repository import (
        DatabaseSchemaError,
        TrackRepository,
        UnsupportedDatabaseVersionError,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "DatabaseSchemaError": ("xfinaudio.library.track_repository", "DatabaseSchemaError"),
    "MetadataScanService": ("xfinaudio.library.scan_service", "MetadataScanService"),
    "TrackRecord": ("xfinaudio.library.models", "TrackRecord"),
    "TrackRepository": ("xfinaudio.library.track_repository", "TrackRepository"),
    "UnsupportedDatabaseVersionError": ("xfinaudio.library.track_repository", "UnsupportedDatabaseVersionError"),
    "plan_supported_audio_paths": ("xfinaudio.library.scan_planning", "plan_supported_audio_paths"),
    "scan_folder": ("xfinaudio.library.scan_service", "scan_folder"),
}

__all__ = [
    "DatabaseSchemaError",
    "MetadataScanService",
    "TrackRecord",
    "TrackRepository",
    "UnsupportedDatabaseVersionError",
    "plan_supported_audio_paths",
    "scan_folder",
]


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily to keep pure library imports isolated."""
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
