"""Lazy path lookup using live items whose row follows native Qt sorting."""

from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


class LibraryPathIndex:
    def __init__(self, table: QTableWidget, *, path_column: int) -> None:
        self._table = table
        self._path_column = path_column
        self._items: dict[str, QTableWidgetItem] | None = None
        model = table.model()
        model.modelReset.connect(self._invalidate)
        model.rowsInserted.connect(self._invalidate)
        model.rowsRemoved.connect(self._invalidate)
        model.dataChanged.connect(self._data_changed)

    def _invalidate(self, *_args: object) -> None:
        self._items = None

    def _data_changed(self, top: QModelIndex, bottom: QModelIndex, *_args: object) -> None:
        if top.column() <= self._path_column <= bottom.column():
            self._invalidate()

    def row_for_path(self, path: str) -> int | None:
        if self._items is None:
            self._items = {}
            for row in range(self._table.rowCount()):
                item = self._table.item(row, self._path_column)
                if item is not None:
                    self._items.setdefault(item.text(), item)
        item = self._items.get(path)
        # Native layout changes keep the item alive and update its row; keeping
        # live items avoids rebuilding the index every time Color sorting moves it.
        return None if item is None or item.row() < 0 else item.row()
