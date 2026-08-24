"""Pure presentation helpers for the library track table."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xfinaudio.desktop.library_columns import COLUMNS
from xfinaudio.desktop.library_view_model import TrackDisplayRow

_DASH = "—"


def _duration_seconds(row: TrackDisplayRow) -> float:
    if row.duration == _DASH:
        return float("inf")
    minutes, seconds = row.duration.split(":")
    return int(minutes) * 60 + int(seconds)


# Keyed by column name, not position: a reordered or inserted column changes the
# index but never which value a column sorts by.
_SORT_KEYS: dict[str, Callable[[TrackDisplayRow], Any]] = {
    "Title": lambda row: row.title.casefold(),
    "Artist": lambda row: row.artist.casefold(),
    "BPM": lambda row: float("inf") if row.bpm == _DASH else float(row.bpm),
    "Key": lambda row: row.musical_key.casefold(),
    "Energy": lambda row: float("inf") if row.energy == _DASH else int(row.energy),
    "LUFS": lambda row: float("inf") if row.lufs == _DASH else float(row.lufs),
    "Duration": _duration_seconds,
    "Color": lambda row: row.spectral_color.casefold(),
    "Missing": lambda row: row.missing_fields.casefold(),
    "Genre": lambda row: row.genre.casefold(),
    "Status": lambda row: row.metadata_status.casefold(),
    "Preview": lambda _row: "",
    "Path": lambda row: row.path.casefold(),
}

# Columns whose absent value is float("inf") and must therefore park at the end
# rather than lead a descending sweep.
_NUMERIC_COLUMNS = frozenset({"BPM", "Energy", "LUFS", "Duration"})


def _column_name(column: int) -> str | None:
    return COLUMNS[column] if 0 <= column < len(COLUMNS) else None


def sort_key_for_column(row: TrackDisplayRow, column: int) -> Any:
    """Return a sortable value for a display row and table column."""
    name = _column_name(column)
    if name is None:
        return ""
    return _SORT_KEYS[name](row)


def sort_rows_for_column(rows: list[TrackDisplayRow], column: int, *, ascending: bool) -> list[TrackDisplayRow]:
    """Sort rows while keeping missing numeric values at the end."""
    numeric = _column_name(column) in _NUMERIC_COLUMNS
    present: list[TrackDisplayRow] = []
    missing: list[TrackDisplayRow] = []
    for row in rows:
        target = missing if numeric and sort_key_for_column(row, column) == float("inf") else present
        target.append(row)
    return sorted(present, key=lambda row: sort_key_for_column(row, column), reverse=not ascending) + missing
