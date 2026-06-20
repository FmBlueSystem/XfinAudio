"""Filesystem-safe export filename generation."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


_RE_UNSAFE = re.compile(r"[^a-zA-Z0-9._-]+")
_RE_DUPE_UNDERSCORE = re.compile(r"_+")


def _sanitize(value: str) -> str:
    """Make a string safe for use in a filesystem path component."""
    cleaned = _RE_UNSAFE.sub("_", value.strip())
    cleaned = _RE_DUPE_UNDERSCORE.sub("_", cleaned)
    return cleaned.strip("_-").lower()


def default_export_filename(
    recommendation: PlaylistRecommendation,
    *,
    generated_at: datetime | None = None,
    suffix: str | None = None,
) -> str:
    """Build a descriptive, filesystem-safe default export filename stem.

    The returned value does not include an extension. Callers append the
    appropriate extension for the target DJ software.
    """
    generated_at = generated_at or datetime.now()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S")
    strategy_name = _sanitize(recommendation.strategy.name)
    count = len(recommendation.ordered_tracks)
    track_word = "track" if count == 1 else "tracks"

    parts = [timestamp, strategy_name]
    if suffix:
        safe_suffix = _sanitize(suffix)
        if safe_suffix:
            parts.append(safe_suffix)
    parts.append(f"{count}_{track_word}")

    return "_".join(parts)
