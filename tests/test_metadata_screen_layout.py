"""Layout tests for the Metadata Worklist screen."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.screens.metadata_screen import MetadataScreen


def test_worklist_table_uses_the_free_vertical_space(qapp: QApplication) -> None:
    """A trailing addStretch(1) competed with the table for the free height.

    Measured at 1200x660: the table got 172px, about five visible rows, or 26%
    of the screen, while the spacer below it took the rest.

    The empty-state label shares the same stretch factor, so it is hidden here
    to measure the state that actually matters -- a scanned library.
    """
    screen = MetadataScreen()
    screen.resize(1200, 660)
    screen.show()
    screen.worklist_empty_label.hide()
    qapp.processEvents()

    table = screen.worklist_table
    row_height = max(table.verticalHeader().defaultSectionSize(), 1)

    assert table.viewport().height() // row_height >= 10
    assert table.height() > 0.5 * screen.height()
