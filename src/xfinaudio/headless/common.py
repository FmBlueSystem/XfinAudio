"""Safe headless error, identity, and input helpers shared by command adapters."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from xfinaudio.library.models import TrackRecord


class BackendError(Exception):
    """A safe-to-display command failure; never includes private filesystem paths."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve(strict=True).is_relative_to(root) and path.resolve(strict=True) == path
    except (OSError, RuntimeError):
        return False


def _public_track(track: TrackRecord) -> dict[str, Any]:
    return {
        "id": hashlib.sha256(track.path.encode("utf-8")).hexdigest(),
        "title": track.title or Path(track.path).stem,
        "artist": track.artist or "",
        "bpm": track.bpm,
        "key": track.camelot_key,
        "energy": track.energy_level,
        "duration": track.duration,
        "genre": track.genre or "",
        "audioFormat": track.audio_format,
        "audioCodec": track.audio_codec,
        "bitrateKbps": track.bitrate_kbps,
        "bitrateMode": track.bitrate_mode,
        "status": track.metadata_status,
        "missingFields": list(track.missing_required_fields),
    }


def _text(value: Any, label: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise BackendError("invalid_params", f"Invalid {label}")
    return value.strip()
