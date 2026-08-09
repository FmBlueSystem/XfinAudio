from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.screens.build_screen import _COPILOT_COLUMNS, ANY_GENRE, BuildScreen


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


def test_all_buttons_have_tooltips(qapp: QApplication) -> None:
    """Every QPushButton on the screen exposes a non-empty tooltip (R1)."""
    from PySide6.QtWidgets import QPushButton

    screen = BuildScreen()

    buttons = screen.findChildren(QPushButton)
    assert buttons
    assert all(button.toolTip().strip() for button in buttons)


def test_copilot_table_headers_have_tooltips(qapp: QApplication) -> None:
    """Every copilot table column header carries an explanatory tooltip (R2)."""
    screen = BuildScreen()

    table = screen.copilot_table
    tooltips = [table.horizontalHeaderItem(col).toolTip() for col in range(table.columnCount())]
    assert all(tip.strip() for tip in tooltips)


def test_strategy_combo_shows_display_names_and_stores_internal_name_as_data(qapp: QApplication) -> None:
    """Combo items show display_name; itemData carries the internal strategy name.

    Spec `strategy-selection-ux` -> "Selector Shows Display Names".
    """
    screen = BuildScreen()
    vm = BuildViewModel()

    screen.render(vm, AppState(), lightweight=True)

    options = vm.available_strategies()
    assert screen.strategy_combo.count() == len(options)
    for index, option in enumerate(options):
        assert screen.strategy_combo.itemText(index) == option.display_name
        assert screen.strategy_combo.itemText(index) != option.name
        assert screen.strategy_combo.itemData(index) == option.name


def test_on_recommend_emits_internal_strategy_name_via_current_data(qapp: QApplication) -> None:
    """`_on_recommend` emits the internal strategy name (currentData), not the display label.

    Spec `strategy-selection-ux` -> "Selecting a display name resolves the internal strategy".
    """
    screen = BuildScreen()
    vm = BuildViewModel()
    screen.render(vm, AppState(), lightweight=True)

    target_index = screen.strategy_combo.findData("same_color_energy")
    assert target_index >= 0
    screen.strategy_combo.setCurrentIndex(target_index)

    emitted: list[str] = []
    screen.recommend_requested.connect(lambda strategy, _paths: emitted.append(strategy))

    screen._on_recommend()

    assert emitted == ["same_color_energy"]
    assert screen.strategy_combo.currentText() != "same_color_energy"


def test_strategy_explanation_label_refreshes_immediately_on_selection_change(qapp: QApplication) -> None:
    """The explanation label updates as soon as the combo selection changes, without a re-render.

    Spec `strategy-selection-ux` -> "Immediate Description Refresh on Selection".
    """
    screen = BuildScreen()
    vm = BuildViewModel()
    screen.render(vm, AppState(), lightweight=True)

    same_color_index = screen.strategy_combo.findData("same_color")
    same_color_energy_index = screen.strategy_combo.findData("same_color_energy")
    assert same_color_index >= 0
    assert same_color_energy_index >= 0

    screen.strategy_combo.setCurrentIndex(same_color_index)
    assert screen.strategy_explanation_label.text() == vm.strategy_explanation("same_color")

    screen.strategy_combo.setCurrentIndex(same_color_energy_index)

    assert screen.strategy_explanation_label.text() == vm.strategy_explanation("same_color_energy")


def test_selecting_strategy_by_display_name_resolves_to_internal_strategy_name(qapp: QApplication) -> None:
    """Selecting a combo item by its display label still resolves to the internal strategy name
    used for downstream generation and persistence/export.

    Spec `strategy-selection-ux` -> "Persisted and Exported Artifacts Record Internal Names".
    """
    from xfinaudio.recommendation.strategies import default_strategy_registry

    screen = BuildScreen()
    vm = BuildViewModel()
    screen.render(vm, AppState(), lightweight=True)

    display_label = "Same Color & Energy"
    index = screen.strategy_combo.findText(display_label)
    assert index >= 0
    screen.strategy_combo.setCurrentIndex(index)

    internal_name = screen.strategy_combo.currentData()
    assert internal_name == "same_color_energy"
    assert internal_name != display_label

    resolved = default_strategy_registry().get(internal_name)
    assert resolved.name == "same_color_energy"


def test_copilot_table_uses_the_free_vertical_space(qapp: QApplication) -> None:
    """A trailing addStretch(1) competed with the table for the free height.

    Measured at 1200x660: the table got 127px, about three visible rows, or 19%
    of the screen, while the spacer below it took the rest.
    """
    screen = BuildScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    table = screen.copilot_table
    row_height = max(table.verticalHeader().defaultSectionSize(), 1)

    # The screen carries a lot of controls above the table, so it will never own
    # most of the height; 127px was the spacer stealing what was left.
    assert table.viewport().height() // row_height >= 6
    assert table.height() > 0.33 * screen.height()


def test_copilot_description_column_is_wider_than_the_count_column(qapp: QApplication) -> None:
    """Description holds a sentence; Tracks holds a number. They were both 294px."""
    screen = BuildScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    header = screen.copilot_table.horizontalHeader()
    width = {name: header.sectionSize(index) for index, name in enumerate(_COPILOT_COLUMNS)}

    # A plain ">" would pass on the 294 vs 293 rounding of an even split.
    assert width["Description"] > 2 * width["Tracks"]
    assert width["Description"] > width["Readiness"]


def test_anchor_genre_suggestion_selects_an_offered_genre(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])

    screen.suggest_genre_from_anchor("House")

    assert screen.genre_combo.currentText() == "House"


def test_anchor_genre_suggestion_leaves_selection_for_unavailable_or_missing_genre(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])
    screen.genre_combo.setCurrentText("Rock")

    screen.suggest_genre_from_anchor("Techno")
    assert screen.genre_combo.currentText() == "Rock"

    screen.suggest_genre_from_anchor(None)
    assert screen.genre_combo.currentText() == "Rock"


def test_programmatic_anchor_suggestions_do_not_count_as_a_dj_choice(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])

    screen.suggest_genre_from_anchor("House")
    screen.suggest_genre_from_anchor("Rock")

    assert screen.genre_combo.currentText() == "Rock"


def test_dj_genre_choice_wins_over_later_anchor_suggestions(qapp: QApplication) -> None:
    screen = BuildScreen()
    screen.set_available_genres(["House", "Rock"])
    any_genre_index = screen.genre_combo.findText(ANY_GENRE)
    screen.genre_combo.setCurrentIndex(any_genre_index)
    screen.genre_combo.activated.emit(any_genre_index)

    screen.suggest_genre_from_anchor("House")

    assert screen.genre_combo.currentText() == ANY_GENRE
