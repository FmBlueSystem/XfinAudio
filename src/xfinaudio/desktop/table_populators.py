"""Focused Qt table population helpers for desktop library and recommendation rows."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord

TableItemFactory = Callable[[str, object | None], QTableWidgetItem]


def populate_library_table(
    table: QTableWidget,
    records: Sequence[TrackRecord],
    *,
    item_factory: TableItemFactory,
    format_missing_metadata: Callable[[TrackRecord], str],
    format_track_tags: Callable[[TrackRecord], str],
) -> dict[str, TrackRecord]:
    """Populate library track rows and return the path-to-record lookup."""
    table.setRowCount(len(records))
    records_by_path = {record.path: record for record in records}
    for row_index, record in enumerate(records):
        values = [
            record.title or "",
            record.artist or "",
            "" if record.bpm is None else f"{record.bpm:g}",
            record.camelot_key or "",
            "" if record.energy_level is None else str(record.energy_level),
            format_missing_metadata(record),
            record.genre or "",
            format_track_tags(record),
            record.metadata_status,
            record.path,
        ]
        sort_values: list[object] = [
            values[0].casefold(),
            values[1].casefold(),
            record.bpm if record.bpm is not None else float("inf"),
            values[3].casefold(),
            values[4].casefold(),
            values[5].casefold(),
            record.energy_level if record.energy_level is not None else 999,
            values[5].casefold(),
            values[6].casefold(),
            values[7].casefold(),
            values[8].casefold(),
            values[9].casefold(),
        ]
        for column_index, value in enumerate(values):
            table.setItem(row_index, column_index, item_factory(value, sort_values[column_index]))
    return records_by_path


def populate_recommendation_table(
    table: QTableWidget,
    records: Sequence[TrackRecord],
    strategy_name: str,
    explanation: PlaylistExplanation | None,
    *,
    item_factory: TableItemFactory,
    format_track_tags: Callable[[TrackRecord], str],
    format_warning: Callable[[str], str],
) -> None:
    """Populate recommendation table rows from records and optional transition explanations."""
    table.setRowCount(len(records))
    transition_rows = explanation.transitions if explanation is not None else []
    for row_index, record in enumerate(records):
        transition = transition_rows[row_index - 1] if row_index > 0 and row_index - 1 < len(transition_rows) else None
        values = [
            record.title or "",
            record.artist or "",
            "" if record.bpm is None else f"{record.bpm:g}",
            record.camelot_key or "",
            "" if record.energy_level is None else str(record.energy_level),
            record.genre or "",
            format_track_tags(record),
            strategy_name,
            record.path,
            "" if transition is None else f"{transition.final_score:.3f}",
            "" if transition is None else "; ".join(format_warning(warning) for warning in transition.warnings),
        ]
        sort_values: list[object] = [
            values[0].casefold(),
            values[1].casefold(),
            record.bpm if record.bpm is not None else float("inf"),
            values[3].casefold(),
            values[4].casefold(),
            values[5].casefold(),
            record.energy_level if record.energy_level is not None else 999,
            values[5].casefold(),
            values[6].casefold(),
            values[7].casefold(),
            values[8].casefold(),
            transition.final_score if transition is not None else -1.0,
            values[10].casefold(),
        ]
        for column_index, value in enumerate(values):
            table.setItem(row_index, column_index, item_factory(value, sort_values[column_index]))
