"""Prep Copilot controller for MainWindow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QTableWidgetItem

from xfinaudio.desktop.app_state_transitions import (
    PrepCopilotVariantApplication,
    apply_prep_copilot_variant,
)
from xfinaudio.desktop.rendering import format_quality_summary
from xfinaudio.exporting.explainability import build_playlist_explanation
from xfinaudio.quality.dj_readiness import format_dj_readiness_summary
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan


class PrepCopilotController:
    def __init__(
        self,
        *,
        build_screen: Any,
        build_vm: Any,
        state: Any,
        workflow_service: Any,
        on_state_changed: Callable[[], None],
        on_status_message: Callable[[str], None],
    ) -> None:
        self._build_screen = build_screen
        self._build_vm = build_vm
        self._state = state
        self._workflow_service = workflow_service
        self._on_state_changed = on_state_changed
        self._on_status_message = on_status_message

    def generate(self) -> None:
        controls = self._state._selected_track_controls()
        if controls is None:
            self._state.last_prep_copilot_plan = None
            self._build_screen.copilot_table.setRowCount(0)
            self._build_screen.apply_variant_button.setEnabled(False)
            self._on_status_message(self._state.tr("Select at least one complete track before generating Prep Copilot"))
            return
        records = self._state._desktop_recommendation_records(controls)
        genre_focus = self._build_screen.genre_focus_input.text().strip() or None
        intent = DJSetIntent(
            name="Desktop Prep Copilot",
            strategy=self._build_screen.strategy_combo.currentData() or self._build_screen.strategy_combo.currentText(),
            target_track_count=self._build_screen.target_count_input.value(),
            start_path=controls.start_path,
            required_paths=controls.manual_order_paths,
            genre_focus=genre_focus,
        )
        plan = build_prep_copilot_plan(records, intent)
        self._state.last_prep_copilot_plan = plan
        self._build_screen.apply_variant_button.setEnabled(True)
        self._on_status_message(self._state.tr("Generated {0} Prep Copilot variant(s)").format(len(plan.variants)))
        self._build_screen.copilot_table.setHidden(len(plan.variants) == 0)
        self._build_screen.render(self._build_vm, self._state._state)
        self._on_state_changed()

    def apply_item(self, item: QTableWidgetItem) -> None:
        self._build_screen.copilot_table.selectRow(item.row())
        self.apply_selected_variant()

    def apply_selected_variant(self) -> None:
        if self._state.last_prep_copilot_plan is None:
            self._on_status_message(self._state.tr("Generate and select a Prep Copilot variant before applying"))
            return
        selected_rows = sorted({index.row() for index in self._build_screen.copilot_table.selectedIndexes()})
        if not selected_rows:
            self._on_status_message(self._state.tr("Generate and select a Prep Copilot variant before applying"))
            return
        row_index = selected_rows[0]
        if row_index >= len(self._state.last_prep_copilot_plan.variants):
            self._on_status_message(self._state.tr("Generate and select a Prep Copilot variant before applying"))
            return
        variant = self._state.last_prep_copilot_plan.variants[row_index]
        recommendation = variant.recommendation
        explanation = build_playlist_explanation(recommendation)
        quality_report = build_quality_report(recommendation)
        updated_state = apply_prep_copilot_variant(
            self._state._state,
            PrepCopilotVariantApplication(
                recommendation=recommendation,
                explanation=explanation,
                quality_report=quality_report,
                readiness_report=variant.readiness,
                variant_name=variant.name,
            ),
        )
        if hasattr(self._state, "_replace_app_state"):
            self._state._replace_app_state(updated_state)
        else:
            self._state._state = updated_state
        self._on_state_changed()
        self._render_applied_variant_label(variant.name)
        self._state.show_recommendation(recommendation.ordered_tracks, recommendation.strategy.name, explanation)
        self._state._review_screen.review_summary_label.setText(format_quality_summary(quality_report))
        self._state._review_screen.dj_readiness_label.setText(format_dj_readiness_summary(variant.readiness))
        self._state._populate_dj_readiness_table(variant.readiness)
        self._state.show_transition_review(explanation)
        self._state._export_screen.export_guidance_label.setText(
            self._state.tr("Inspect the selected Prep Copilot variant before exporting it to Serato.")
        )
        self._on_status_message(self._state.tr("Applied Prep Copilot variant: {0}").format(variant.name))

    def on_variant_applied(self, index: int) -> None:
        if 0 <= index < self._build_screen.copilot_table.rowCount():
            self._build_screen.copilot_table.selectRow(index)
        self.apply_selected_variant()

    def set_applied_variant(self, variant_name: str | None) -> None:
        self._state.applied_prep_copilot_variant_name = variant_name
        self._on_state_changed()
        self._render_applied_variant_label(variant_name)

    def _render_applied_variant_label(self, variant_name: str | None) -> None:
        variant_label = self._build_screen.applied_copilot_variant_label
        if variant_name is None:
            variant_label.setText(self._state.tr("Applied Variant: none"))
            variant_label.setToolTip(self._state.tr("No Prep Copilot variant is currently applied."))
            return
        variant_label.setText(self._state.tr("Applied Variant: {0}").format(variant_name))
        variant_label.setToolTip(self._state.tr("This variant will be used for Serato preview/export."))
