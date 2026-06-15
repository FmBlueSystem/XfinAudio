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
