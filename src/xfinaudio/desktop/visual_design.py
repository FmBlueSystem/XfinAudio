"""Visual design setup for MainWindow."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QSizePolicy, QVBoxLayout

from xfinaudio.desktop.theme import (
    _COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT,
    _COMPACT_REVIEW_TABLE_MIN_HEIGHT,
    _COMPACT_TABLE_ROW_HEIGHT,
    _DJ_READINESS_TABLE_COLUMN_WIDTHS,
    _DJ_VISUAL_STYLESHEET,
    _REVIEW_TABLE_COLUMN_WIDTHS,
    _SERATO_EXPORT_HISTORY_COLUMN_WIDTHS,
    _TRACK_TABLE_COLUMN_WIDTHS,
)


def apply_compact_mac_layout(window: Any, layout: QVBoxLayout, status_controls: QHBoxLayout) -> None:
    layout.setContentsMargins(10, 8, 10, 10)
    layout.setSpacing(6)
    status_controls.setSpacing(8)
    window._build_screen.recommend_button.setMinimumWidth(220)
    window._build_screen.recommend_button.setMaximumWidth(260)
    window._build_screen.copilot_button.setMinimumWidth(190)
    window._build_screen.copilot_button.setMaximumWidth(220)
    window._build_screen.apply_variant_button.setMaximumWidth(220)
    window._build_screen.genre_focus_input.setMinimumWidth(160)
    window._build_screen.genre_focus_input.setMaximumWidth(360)
    window._metadata_screen.status_combo.setMaximumWidth(170)
    window._metadata_screen.missing_combo.setMaximumWidth(220)
    window._metadata_screen.export_button.setMaximumWidth(220)
    window._library_screen.tracks_table.setMinimumHeight(400)
    window._library_screen.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    window._review_screen.transition_table.setMinimumHeight(_COMPACT_REVIEW_TABLE_MIN_HEIGHT)
    window._review_screen.transition_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    window._review_screen.readiness_table.setMaximumHeight(_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT)
    window._review_screen.readiness_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    window._export_screen.history_table.setMaximumHeight(_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT)
    window._export_screen.history_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    apply_compact_table_columns(window)
    window._set_recommendation_sections_expanded(False)


def apply_compact_table_columns(window: Any) -> None:
    table_widths = (
        (window._library_screen.tracks_table, _TRACK_TABLE_COLUMN_WIDTHS),
        (window._review_screen.transition_table, _REVIEW_TABLE_COLUMN_WIDTHS),
        (window._review_screen.readiness_table, _DJ_READINESS_TABLE_COLUMN_WIDTHS),
        (window._export_screen.history_table, _SERATO_EXPORT_HISTORY_COLUMN_WIDTHS),
    )
    for table, widths in table_widths:
        for column_index, width in enumerate(widths):
            table.horizontalHeader().setSectionResizeMode(column_index, QHeaderView.ResizeMode.Interactive)
            table.setColumnWidth(column_index, width)
        table.horizontalHeader().setStretchLastSection(True)


def apply_visual_design(window: Any) -> None:
    window._build_screen.recommend_button.setObjectName("primaryAction")
    window._library_screen.search_input.setObjectName("songSearch")
    window.status_label.setObjectName("statusLabel")
    for label in (
        window.folder_label,
        window.library_guidance_label,
        window.scan_progress_label,
        window.recommendation_guidance_label,
        window._export_screen.export_guidance_label,
        window._export_screen.safe_export_folder_label,
        window.library_decision_label,
        window.metadata_decision_label,
    ):
        label.setObjectName("guidanceLabel")
    for table in (
        window._library_screen.tracks_table,
        window._review_screen.transition_table,
        window._review_screen.readiness_table,
        window._export_screen.history_table,
    ):
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.verticalHeader().setDefaultSectionSize(_COMPACT_TABLE_ROW_HEIGHT)
        table.verticalHeader().setMinimumSectionSize(_COMPACT_TABLE_ROW_HEIGHT)
        table.verticalHeader().setVisible(False)
    window._library_screen.search_input.setClearButtonEnabled(True)
    window.setStyleSheet(_DJ_VISUAL_STYLESHEET)
