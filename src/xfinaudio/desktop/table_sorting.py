"""Table sorting wiring for desktop tables."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt


def connect_table_sorting(
    table: Any,
    sort_orders: dict[int, Qt.SortOrder],
    on_library_resort: Callable[[], None] | None,
) -> None:
    header = table.horizontalHeader()
    header.setSectionsClickable(True)
    header.setSortIndicatorShown(True)
    header.sectionClicked.connect(
        lambda column, table=table: sort_table_by_column(table, column, sort_orders, on_library_resort)
    )


def sort_table_by_column(
    table: Any,
    column: int,
    sort_orders: dict[int, Qt.SortOrder],
    on_library_resort: Callable[[], None] | None,
) -> None:
    sort_key = id(table) * 1000 + column
    previous_order = sort_orders.get(sort_key)
    order = (
        Qt.SortOrder.DescendingOrder if previous_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
    )
    sort_orders.clear()
    sort_orders[sort_key] = order
    table.sortItems(column, order)
    table.horizontalHeader().setSortIndicator(column, order)
    if on_library_resort is not None:
        on_library_resort()
