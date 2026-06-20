"""Library scanning and persistence APIs."""

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_planning import plan_supported_audio_paths
from xfinaudio.library.scan_service import MetadataScanService, scan_folder
from xfinaudio.library.track_repository import DatabaseSchemaError, TrackRepository, UnsupportedDatabaseVersionError

__all__ = [
    "DatabaseSchemaError",
    "MetadataScanService",
    "TrackRecord",
    "TrackRepository",
    "plan_supported_audio_paths",
    "UnsupportedDatabaseVersionError",
    "scan_folder",
]
