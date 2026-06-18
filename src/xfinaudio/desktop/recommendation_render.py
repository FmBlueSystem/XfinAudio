"""Recommendation rendering helpers for MainWindow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xfinaudio.desktop.rendering import (
    _component_score,
    _format_review_score,
    _score_sort_value,
    _table_item,
    _track_review_name,
    format_recommendation_warning,
)
from xfinaudio.desktop.table_populators import populate_transition_review_table


def render_recommendation(
    *,
    records: list[Any],
    set_sections_expanded: Callable[[bool], None],
    sync_state: Callable[[], None],
    render_tab: Callable[[int], None],
    **_: Any,
) -> None:
    set_sections_expanded(bool(records))
    sync_state()
    render_tab(2)


def clear_recommendation_review(
    *,
    review_screen: Any,
    build_screen: Any,
    empty_summary: str,
    tr: Callable[[str], str],
    set_sections_expanded: Callable[[bool], None],
    **_: Any,
) -> None:
    review_screen.review_summary_label.setText(empty_summary)
    review_screen.dj_readiness_label.setText(tr("DJ Readiness: No recommendation ready."))
    review_screen.readiness_table.setRowCount(0)
    review_screen.transition_table.setRowCount(0)
    build_screen.copilot_table.setHidden(True)
    if review_screen.recommendation_table.rowCount() == 0:
        set_sections_expanded(False)


def show_transition_review(*, review_screen: Any, explanation: Any, **_: Any) -> None:
    populate_transition_review_table(
        review_screen.transition_table,
        explanation,
        item_factory=_table_item,
        format_review_score=_format_review_score,
        component_score=_component_score,
        score_sort_value=_score_sort_value,
        track_review_name=_track_review_name,
        format_warning=format_recommendation_warning,
    )
