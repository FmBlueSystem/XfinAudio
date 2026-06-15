from __future__ import annotations

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.screens.build_screen import BuildScreen


def test_recommend_progress_bar_shows_eta_and_hides_when_complete(qapp: QApplication) -> None:
    screen = BuildScreen()
    vm = BuildViewModel()

    screen.render(
        vm,
        AppState(
            is_recommending=True,
            recommend_progress_count=2,
            recommend_progress_total=5,
            recommend_elapsed_seconds=60,
        ),
        lightweight=True,
    )

    assert screen.recommend_progress_bar.isHidden() is False
    assert screen.recommend_progress_bar.value() == 40
    assert screen.recommend_progress_label.text() == "40% · 1:30 remaining"
    screen.render(vm, AppState(), lightweight=True)
    assert screen.recommend_progress_bar.isHidden() is True
    assert screen.recommend_progress_label.text() == ""
