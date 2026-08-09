from __future__ import annotations

from PySide6.QtWidgets import QApplication, QPushButton

from xfinaudio.desktop.screens.review_screen import _READINESS_COLUMNS, _TRANSITION_COLUMNS, ReviewScreen


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


def test_summary_score_is_reported_once(qapp: QApplication) -> None:
    """Two labels showed the same numbers in different formats, stacked.

    review_summary_label already carries the transition count, warning count and
    average score, and ten call sites drive it. quality_label restated a subset
    of that one line below, and nothing outside this screen referenced it.
    """
    screen = ReviewScreen()

    assert hasattr(screen, "review_summary_label")
    assert not hasattr(screen, "quality_label"), "the duplicate summary label is back"


def test_transition_columns_give_space_to_track_names_not_scores(qapp: QApplication) -> None:
    """Every column stretched equally, so scores got as much room as track titles.

    Measured at 1200px: all nine columns landed on ~131px, enough for "Order" to
    show a single digit while "From"/"To" truncated the titles that make the row
    readable.
    """
    screen = ReviewScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    header = screen.transition_table.horizontalHeader()
    width = {name: header.sectionSize(index) for index, name in enumerate(_TRANSITION_COLUMNS)}

    for score_column in ("Order", "Key", "BPM", "Energy", "Tag", "Fit", "Blend", "Final"):
        assert width[score_column] < width["From"], f"{score_column} is as wide as the track name column"
        assert width[score_column] < width["To"], f"{score_column} is as wide as the track name column"


def test_transition_table_exposes_fit_and_blend_headers(qapp: QApplication) -> None:
    screen = ReviewScreen()
    table = screen.transition_table

    assert table.columnCount() == 11
    assert [table.horizontalHeaderItem(column).text() for column in range(11)] == [
        "Order",
        "From",
        "To",
        "Key",
        "BPM",
        "Energy",
        "Fit",
        "Blend",
        "Tag",
        "Final",
        "Warnings",
    ]
    assert table.horizontalHeaderItem(6).toolTip() == (
        "Do these tracks belong in the same set? Harmony, tags, danceability and spectral colour."
    )
    assert table.horizontalHeaderItem(7).toolTip() == (
        "Can these tracks be joined? Tempo and the energy handoff from the outgoing to the incoming section."
    )
    # Deliberately strategy-agnostic: the old text pinned harmonic_journey's
    # weights but was shown for every strategy.
    final_tooltip = table.horizontalHeaderItem(9).toolTip()
    assert final_tooltip.startswith("Weighted average")
    assert "depend on the selected strategy" in final_tooltip


def test_readiness_detail_column_gets_the_free_width(qapp: QApplication) -> None:
    """Check and Status hold short labels; Detail holds the sentence."""
    screen = ReviewScreen()
    screen.resize(1200, 660)
    screen.show()
    qapp.processEvents()

    header = screen.readiness_table.horizontalHeader()
    check, status, detail = (header.sectionSize(index) for index in range(3))

    assert detail > check
    assert detail > status


def test_warning_column_keeps_usable_width_at_a_normal_window_size(qapp: QApplication) -> None:
    """Regression: eleven columns squeezed Warnings down to a sliver.

    Long score headers ("Energy Score", "Tag Score") forced content-sized
    columns far wider than the four characters they show, so the stretched
    Warnings column collapsed to ~16px and the alerts the summary counts
    were unreadable.
    """
    screen = ReviewScreen()
    screen.resize(1440, 900)
    screen.show()
    qapp.processEvents()

    header = screen.transition_table.horizontalHeader()
    widths = {_TRANSITION_COLUMNS[index]: header.sectionSize(index) for index in range(len(_TRANSITION_COLUMNS))}

    assert widths["Warnings"] >= 120, f"Warnings collapsed to {widths['Warnings']}px"
    for score_column in ("Key", "BPM", "Energy", "Fit", "Blend", "Tag", "Final"):
        assert widths[score_column] <= 90, f"{score_column} takes {widths[score_column]}px for a 5-character score"


def test_theme_column_widths_cover_every_table_column() -> None:
    """Regression: the width tuple silently fell behind the column list.

    `_REVIEW_TABLE_COLUMN_WIDTHS` held nine entries after the table grew to
    eleven columns, so every width landed on the wrong column and the last two
    got none — Warnings collapsed to 17px at 1440px wide. Nothing failed;
    the table just looked wrong.
    """
    from xfinaudio.desktop.theme import (
        _DJ_READINESS_TABLE_COLUMN_WIDTHS,
        _REVIEW_TABLE_COLUMN_WIDTHS,
    )

    assert len(_REVIEW_TABLE_COLUMN_WIDTHS) == len(_TRANSITION_COLUMNS)
    assert len(_DJ_READINESS_TABLE_COLUMN_WIDTHS) == len(_READINESS_COLUMNS)
