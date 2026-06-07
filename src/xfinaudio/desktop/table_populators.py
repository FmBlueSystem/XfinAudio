"""Focused Qt table population helpers for desktop library and recommendation rows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan

TableItemFactory = Callable[[str, object | None], QTableWidgetItem]


def populate_library_table(
    table: QTableWidget,
    records: Sequence[TrackRecord],
    *,
    item_factory: TableItemFactory,
    format_missing_metadata: Callable[[TrackRecord], str],
    format_track_tags: Callable[[TrackRecord], str],
) -> dict[str, TrackRecord]:
    """Populate library track rows and return the path-to-record lookup."""
    table.setRowCount(len(records))
    records_by_path = {record.path: record for record in records}
    for row_index, record in enumerate(records):
        values = [
            record.title or "",
            record.artist or "",
            "" if record.bpm is None else f"{record.bpm:g}",
            record.camelot_key or "",
            "" if record.energy_level is None else str(record.energy_level),
            format_missing_metadata(record),
            record.genre or "",
            format_track_tags(record),
            record.metadata_status,
            record.path,
        ]
        sort_values: list[object] = [
            values[0].casefold(),
            values[1].casefold(),
            record.bpm if record.bpm is not None else float("inf"),
            values[3].casefold(),
            values[4].casefold(),
            values[5].casefold(),
            record.energy_level if record.energy_level is not None else 999,
            values[5].casefold(),
            values[6].casefold(),
            values[7].casefold(),
            values[8].casefold(),
            values[9].casefold(),
        ]
        for column_index, value in enumerate(values):
            table.setItem(row_index, column_index, item_factory(value, sort_values[column_index]))
    return records_by_path


def populate_recommendation_table(
    table: QTableWidget,
    records: Sequence[TrackRecord],
    strategy_name: str,
    explanation: PlaylistExplanation | None,
    *,
    item_factory: TableItemFactory,
    format_track_tags: Callable[[TrackRecord], str],
    format_warning: Callable[[str], str],
) -> None:
    """Populate recommendation table rows from records and optional transition explanations."""
    table.setRowCount(len(records))
    transition_rows = explanation.transitions if explanation is not None else []
    for row_index, record in enumerate(records):
        transition = transition_rows[row_index - 1] if row_index > 0 and row_index - 1 < len(transition_rows) else None
        values = [
            record.title or "",
            record.artist or "",
            "" if record.bpm is None else f"{record.bpm:g}",
            record.camelot_key or "",
            "" if record.energy_level is None else str(record.energy_level),
            record.genre or "",
            format_track_tags(record),
            strategy_name,
            record.path,
            "" if transition is None else f"{transition.final_score:.3f}",
            "" if transition is None else "; ".join(format_warning(warning) for warning in transition.warnings),
        ]
        sort_values: list[object] = [
            values[0].casefold(),
            values[1].casefold(),
            record.bpm if record.bpm is not None else float("inf"),
            values[3].casefold(),
            values[4].casefold(),
            values[5].casefold(),
            record.energy_level if record.energy_level is not None else 999,
            values[5].casefold(),
            values[6].casefold(),
            values[7].casefold(),
            values[8].casefold(),
            transition.final_score if transition is not None else -1.0,
            values[10].casefold(),
        ]
        for column_index, value in enumerate(values):
            table.setItem(row_index, column_index, item_factory(value, sort_values[column_index]))


def populate_dj_readiness_table(
    table: QTableWidget,
    report: DjReadinessReport,
    *,
    item_factory: TableItemFactory,
    readiness_status_labels: dict[str, str],
    readiness_status_colors: dict[str, str],
    readiness_status_tooltips: dict[str, str],
) -> None:
    """Populate the DJ readiness checks table with per-status color coding."""
    table.setRowCount(len(report.checks))
    status_sort = {"blocked": 0, "needs_review": 1, "ready": 2}
    for row_index, check in enumerate(report.checks):
        values = [check.label, readiness_status_labels[check.status], check.detail]
        sort_values: list[object] = [
            check.label.casefold(),
            status_sort[check.status],
            check.detail.casefold(),
        ]
        for column_index, value in enumerate(values):
            item = item_factory(value, sort_values[column_index])
            if column_index == 1:
                item.setBackground(QColor(readiness_status_colors[check.status]))
                item.setForeground(QColor("#061016"))
                item.setToolTip(readiness_status_tooltips[check.status])
            table.setItem(row_index, column_index, item)


def populate_transition_review_table(
    table: QTableWidget,
    explanation: PlaylistExplanation,
    *,
    item_factory: TableItemFactory,
    format_review_score: Callable[[Any], str],
    component_score: Callable[..., Any],
    score_sort_value: Callable[[Any], object],
    track_review_name: Callable[[Any], str],
    format_warning: Callable[[str], str],
) -> None:
    """Populate the transition review table with component scores and warnings."""
    table.setRowCount(len(explanation.transitions))
    for row_index, transition in enumerate(explanation.transitions):
        values = [
            str(transition.order),
            track_review_name(transition.left),
            track_review_name(transition.right),
            format_review_score(component_score(transition, "key_score", "harmonic")),
            format_review_score(component_score(transition, "bpm_score", "bpm")),
            format_review_score(component_score(transition, "energy_score", "energy")),
            format_review_score(component_score(transition, "tag_score", "tags")),
            format_review_score(transition.final_score),
            "; ".join(format_warning(warning) for warning in transition.warnings),
        ]
        sort_values: list[object] = [
            transition.order,
            values[1].casefold(),
            values[2].casefold(),
            score_sort_value(component_score(transition, "key_score", "harmonic")),
            score_sort_value(component_score(transition, "bpm_score", "bpm")),
            score_sort_value(component_score(transition, "energy_score", "energy")),
            score_sort_value(component_score(transition, "tag_score", "tags")),
            score_sort_value(transition.final_score),
            values[8].casefold(),
        ]
        for column_index, value in enumerate(values):
            table.setItem(
                row_index,
                column_index,
                item_factory(value, sort_values[column_index]),
            )


def populate_prep_copilot_table(
    table: QTableWidget,
    plan: PrepCopilotPlan,
    *,
    item_factory: TableItemFactory,
    readiness_status_labels: dict[str, str],
    readiness_status_colors: dict[str, str],
) -> None:
    """Populate the Prep Copilot variants table with readiness color coding."""
    table.setRowCount(len(plan.variants))
    for row_index, variant in enumerate(plan.variants):
        values = [
            variant.name,
            readiness_status_labels[variant.readiness.status],
            str(len(variant.recommendation.ordered_tracks)),
            "; ".join([*variant.blockers, *variant.warnings]),
        ]
        for column_index, value in enumerate(values):
            item = item_factory(value, value.casefold() if isinstance(value, str) else value)
            if column_index == 1:
                item.setBackground(QColor(readiness_status_colors[variant.readiness.status]))
                item.setForeground(QColor("#061016"))
                item.setToolTip(variant.readiness.summary)
            table.setItem(row_index, column_index, item)


def populate_serato_export_history_table(
    table: QTableWidget,
    history: list[dict[str, str]],
    *,
    item_factory: TableItemFactory,
) -> None:
    """Populate the Serato export history table from the most recent export receipts."""
    table.setRowCount(len(history))
    for row_index, export_receipt in enumerate(history):
        values = [
            export_receipt["time"],
            export_receipt["strategy"],
            export_receipt["tracks"],
            export_receipt["path"],
            export_receipt.get("readiness_json_path", ""),
            export_receipt.get("readiness_csv_path", ""),
        ]
        sort_values: list[object] = [
            values[0],
            values[1].casefold(),
            int(values[2]),
            values[3].casefold(),
            values[4].casefold(),
            values[5].casefold(),
        ]
        for column_index, value in enumerate(values):
            item = item_factory(value, sort_values[column_index])
            if column_index in {3, 4, 5}:
                item.setToolTip(value)
            table.setItem(row_index, column_index, item)
