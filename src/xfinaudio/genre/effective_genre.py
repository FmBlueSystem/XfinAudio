"""Centralized genre precedence helper.

Consumers (recommendation, library health, scoring) ask for the effective
genre of a track and get the canonical (enriched) genre when available,
falling back to the raw file-tag genre. This is the single precedence rule
used across the app.
"""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord


def effective_genre(track: TrackRecord) -> str | None:
    """Return the canonical genre if present, else the file-tag genre.

    A canonical genre is "present" when ``track.genre_decision`` is set AND
    its ``primary`` is non-empty. The raw file tag is never overwritten.
    """
    if track.genre_decision is not None and track.genre_decision.primary:
        return track.genre_decision.primary
    return track.genre


__all__ = ["effective_genre"]
