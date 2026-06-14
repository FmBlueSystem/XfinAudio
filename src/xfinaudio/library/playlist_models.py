"""Domain models for playlist persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Playlist:
    """A persisted or in-memory playlist."""

    id: int | None
    name: str
    created_at: datetime
    updated_at: datetime
    track_paths: list[str]


@dataclass(frozen=True)
class PlaylistSummary:
    """Lightweight summary for list views."""

    id: int
    name: str
    track_count: int
    updated_at: datetime
