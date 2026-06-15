from __future__ import annotations

from PySide6.QtWidgets import QApplication

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
