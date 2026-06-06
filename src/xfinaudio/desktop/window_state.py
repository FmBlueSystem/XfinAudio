"""Immutable domain state container for the MainWindow desktop session."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from xfinaudio.library.models import TrackRecord

_EXPORT_HISTORY_LIMIT = 5


@dataclasses.dataclass(frozen=True)
class WindowState:
    """Holds the pure domain state of a desktop session — no Qt dependencies.

    All mutation methods return a new instance; the original is never modified.
    """

    selected_folder: Path | None = None
    active_search_query: str = ""
    _scanned_records: tuple[TrackRecord, ...] = dataclasses.field(default=(), repr=False)
    last_recommendation: Any | None = None
    _export_history: tuple[dict, ...] = dataclasses.field(default=(), repr=False)

    @property
    def scanned_records(self) -> list[TrackRecord]:
        return list(self._scanned_records)

    @property
    def export_history(self) -> list[dict]:
        return list(self._export_history)

    def update_folder(self, folder: Path | None) -> WindowState:
        return dataclasses.replace(self, selected_folder=folder)

    def update_search_query(self, query: str) -> WindowState:
        return dataclasses.replace(self, active_search_query=query)

    def update_scan(self, records: list[TrackRecord]) -> WindowState:
        return dataclasses.replace(self, _scanned_records=tuple(records))

    def clear_scan(self) -> WindowState:
        return dataclasses.replace(self, _scanned_records=())

    def update_recommendation(self, recommendation: Any | None) -> WindowState:
        return dataclasses.replace(self, last_recommendation=recommendation)

    def add_export_entry(self, entry: dict) -> WindowState:
        new_history = (entry, *self._export_history)[:_EXPORT_HISTORY_LIMIT]
        return dataclasses.replace(self, _export_history=new_history)
