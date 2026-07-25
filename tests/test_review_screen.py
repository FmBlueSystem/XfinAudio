from __future__ import annotations

from PySide6.QtWidgets import QApplication, QPushButton

from xfinaudio.desktop.screens.review_screen import ReviewScreen


def test_all_buttons_have_tooltips(qapp: QApplication) -> None:
    """Every QPushButton on the screen exposes a non-empty tooltip (R1)."""
    screen = ReviewScreen()

    buttons = screen.findChildren(QPushButton)
    assert buttons
    assert all(button.toolTip().strip() for button in buttons)


def test_recommendation_table_headers_have_tooltips(qapp: QApplication) -> None:
    """Every recommendation table column header carries an explanatory tooltip (R2)."""
    screen = ReviewScreen()

    table = screen.recommendation_table
    tooltips = [table.horizontalHeaderItem(col).toolTip() for col in range(table.columnCount())]
    assert all(tip.strip() for tip in tooltips)


def test_tables_use_the_free_vertical_space(qapp: QApplication) -> None:
    """The three tables should share the screen, not be squeezed above dead space.

    All three carry stretch factor 1, but a trailing addStretch(1) competed with
    them, so the free height was split four ways and a quarter went to nothing.
    Measured at 1200x660: 108px per table, about two visible rows each, with
    337px left over.
    """
    screen = ReviewScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    tables = (screen.recommendation_table, screen.transition_table, screen.readiness_table)
    visible_rows = [
        table.viewport().height() // max(table.verticalHeader().defaultSectionSize(), 1) for table in tables
    ]

    assert all(rows >= 4 for rows in visible_rows), f"only {visible_rows} rows visible per table"
    assert sum(table.height() for table in tables) > 0.65 * screen.height()
