from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame

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


def test_primary_and_secondary_action_buttons_have_visual_hierarchy(qapp: QApplication) -> None:
    """Recommend is a larger primary action; Back is a smaller muted secondary action."""
    screen = BuildScreen()

    assert screen.recommend_button.objectName() == "primaryAction"
    assert screen.back_button.objectName() == "secondaryAction"
    assert screen.recommend_button.minimumHeight() > screen.back_button.maximumHeight()


def test_section_divider_separates_controls_from_table(qapp: QApplication) -> None:
    """A horizontal QFrame divider sits between the controls and the copilot table."""
    screen = BuildScreen()

    assert screen.section_divider.frameShape() == QFrame.Shape.HLine


def test_empty_state_shows_no_recommendation(qapp: QApplication) -> None:
    """Empty-state label guides the user while no recommendation exists."""
    screen = BuildScreen()
    vm = BuildViewModel()

    screen.render(vm, AppState(), lightweight=True)

    assert screen.empty_state_label.isHidden() is False
    assert "recommend" in screen.empty_state_label.text().casefold()
