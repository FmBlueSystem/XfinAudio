"""Indexed Qt paths remain correct when row order or table contents change."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from xfinaudio.desktop.library_path_index import LibraryPathIndex


@pytest.fixture
def table():
    app = QApplication.instance() or QApplication([])
    widget = QTableWidget(3, 2)
    for row, path in enumerate(("/c", "/a", "/b")):
        widget.setItem(row, 0, QTableWidgetItem(""))
        widget.setItem(row, 1, QTableWidgetItem(path))
    yield widget
    widget.close()
    assert app is not None


def test_index_tracks_live_items_through_sort_and_hidden_filter(table) -> None:
    index = LibraryPathIndex(table, path_column=1)
    assert index.row_for_path("/c") == 0
    table.sortItems(1, Qt.SortOrder.AscendingOrder)
    assert index.row_for_path("/c") == 2
    table.setRowHidden(2, True)
    assert index.row_for_path("/c") == 2
    table.sortItems(1, Qt.SortOrder.DescendingOrder)
    assert index.row_for_path("/c") == 0


def test_index_invalidates_for_rebuild_removal_and_path_edit(table) -> None:
    index = LibraryPathIndex(table, path_column=1)
    assert index.row_for_path("/c") == 0
    table.setItem(0, 1, QTableWidgetItem("/new"))
    assert index.row_for_path("/c") is None
    assert index.row_for_path("/new") == 0
    table.item(0, 1).setText("/edited")
    assert index.row_for_path("/edited") == 0
    table.removeRow(0)
    assert index.row_for_path("/edited") is None
    assert index.row_for_path("/a") == 0
    table.setRowCount(0)
    table.setRowCount(1)
    table.setItem(0, 1, QTableWidgetItem("/b"))
    assert index.row_for_path("/a") is None
    assert index.row_for_path("/b") == 0


def test_repeated_lookup_and_color_sort_do_not_rescan_path_items(table, monkeypatch) -> None:
    calls = []
    original = table.item

    def counted_item(row, column):
        calls.append((row, column))
        return original(row, column)

    monkeypatch.setattr(table, "item", counted_item)
    index = LibraryPathIndex(table, path_column=1)
    assert index.row_for_path("/c") == 0
    assert len(calls) == 3
    table.setSortingEnabled(True)
    table.sortItems(0, Qt.SortOrder.AscendingOrder)
    path_item = original(index.row_for_path("/c"), 1)
    for value in ("RED", "GREEN", "BLUE"):
        row = index.row_for_path("/c")
        original(row, 0).setText(value)
        for _ in range(100):
            assert index.row_for_path("/c") == path_item.row()
    assert len(calls) == 3
