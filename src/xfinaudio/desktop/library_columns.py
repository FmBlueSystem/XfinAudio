"""Single source of truth for the library track table's column contract.

Column order is the contract. Row populators, header labels, pixel widths, sort
keys and every module-level index constant derive from `COLUMNS` here, so adding
or moving a column cannot leave one surface rendering values a position behind
another. This module deliberately imports nothing from `xfinaudio.desktop` so any
module can depend on it without creating a cycle.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

T = TypeVar("T")

COLUMNS: tuple[str, ...] = (
    "Title",
    "Artist",
    "BPM",
    "Key",
    "Energy",
    "LUFS",
    "Duration",
    "Color",
    "Missing",
    "Genre",
    "Status",
    "Preview",
    "Path",
)

COLUMN_WIDTHS: Mapping[str, int] = {
    "Title": 160,
    "Artist": 145,
    "BPM": 70,
    "Key": 70,
    "Energy": 76,
    "LUFS": 76,
    "Duration": 90,
    "Color": 150,
    "Missing": 130,
    "Genre": 140,
    "Status": 86,
    "Preview": 70,
    "Path": 220,
}


def column_index(name: str) -> int:
    """Return a named column's table position, raising if the name is not a column."""
    return COLUMNS.index(name)


def ordered_widths() -> tuple[int, ...]:
    """Return pixel widths in column order, so a width can never land on a neighbour."""
    return tuple(COLUMN_WIDTHS[name] for name in COLUMNS)


def ordered_cells(cells: Mapping[str, T]) -> list[T]:
    """Return one row's cells in column order.

    Populators build a name-keyed mapping instead of a positional list; a column
    added without a matching cell raises here rather than silently shifting the row.
    """
    missing = [name for name in COLUMNS if name not in cells]
    if missing:
        raise KeyError(f"Missing library table cells: {', '.join(missing)}")
    return [cells[name] for name in COLUMNS]


__all__ = ["COLUMNS", "COLUMN_WIDTHS", "column_index", "ordered_cells", "ordered_widths"]
