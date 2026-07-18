"""Pure presentation helpers for the library track table."""

from __future__ import annotations

from typing import Any

from xfinaudio.desktop.library_view_model import TrackDisplayRow


def sort_key_for_column(row: TrackDisplayRow, column: int) -> Any:
    """Return a sortable value for a display row and table column."""
    if column == 0:
        return row.title.casefold()
    if column == 1:
        return row.artist.casefold()
    if column == 2:
        return float("inf") if row.bpm == "—" else float(row.bpm)
    if column == 3:
        return row.musical_key.casefold()
    if column == 4:
        return float("inf") if row.energy == "—" else int(row.energy)
    if column == 5:
        if row.duration == "—":
            return float("inf")
        minutes, seconds = row.duration.split(":")
        return int(minutes) * 60 + int(seconds)
    if column == 6:
        return row.spectral_color.casefold()
    if column == 7:
        return row.missing_fields.casefold()
    if column == 8:
        return row.genre.casefold()
    if column == 9:
        return row.metadata_status.casefold()
    if column == 10:
        return ""
    if column == 11:
        return row.path.casefold()
    return ""
