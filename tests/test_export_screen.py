from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.screens.export_screen import ExportScreen


def test_export_progress_bar_shows_eta_and_hides_when_complete(qapp: QApplication) -> None:
    screen = ExportScreen()
    vm = ExportViewModel()

    screen.render(
        vm,
        AppState(is_exporting=True, export_progress_count=3, export_progress_total=6, export_elapsed_seconds=90),
        lightweight=True,
    )

    assert screen.export_progress_bar.isHidden() is False
    assert screen.export_progress_bar.value() == 50
    assert screen.export_progress_label.text() == "50% · 1:30 remaining"
    screen.render(vm, AppState(), lightweight=True)
    assert screen.export_progress_bar.isHidden() is True
    assert screen.export_progress_label.text() == ""


def test_primary_and_secondary_action_buttons_have_visual_hierarchy(qapp: QApplication) -> None:
    """Export is a larger accent primary action; Back and Preview are smaller muted secondaries.

    The Export button keeps its established ``seratoExportButton`` accent objectName
    (gold primary accent) rather than the generic ``primaryAction`` cyan accent.
    """
    screen = ExportScreen()

    assert screen.export_button.objectName() == "seratoExportButton"
    assert screen.back_button.objectName() == "secondaryAction"
    assert screen.preview_button.objectName() == "secondaryAction"
    assert screen.export_button.minimumHeight() > screen.back_button.maximumHeight()


def test_section_divider_separates_controls_from_table(qapp: QApplication) -> None:
    """A horizontal QFrame divider sits between the controls and the history table."""
    screen = ExportScreen()

    assert screen.section_divider.frameShape() == QFrame.Shape.HLine


def test_all_buttons_have_tooltips(qapp: QApplication) -> None:
    """Every QPushButton on the screen exposes a non-empty tooltip (R1)."""
    from PySide6.QtWidgets import QPushButton

    screen = ExportScreen()

    buttons = screen.findChildren(QPushButton)
    assert buttons
    assert all(button.toolTip().strip() for button in buttons)


def test_history_table_headers_have_tooltips(qapp: QApplication) -> None:
    """Every export-history column header carries an explanatory tooltip (R2)."""
    screen = ExportScreen()

    table = screen.history_table
    tooltips = [table.horizontalHeaderItem(col).toolTip() for col in range(table.columnCount())]
    assert all(tip.strip() for tip in tooltips)
