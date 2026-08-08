"""Prep Copilot controller for MainWindow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from PySide6.QtWidgets import QTableWidgetItem

from xfinaudio.application.dj_readiness import format_application_dj_readiness_summary
from xfinaudio.application.prep_copilot import (
    PrepCopilotGenerationRequest,
    build_prep_copilot_variant_application,
    generate_prep_copilot_plan,
)
from xfinaudio.desktop.app_state_transitions import (
    PrepCopilotVariantApplication,
    apply_prep_copilot_plan_cleared,
    apply_prep_copilot_plan_generated,
    apply_prep_copilot_variant,
)
from xfinaudio.desktop.candidate_routes import (
    ColorAnchorContextRoute,
    RecommendationRecordsRoute,
    resolve_candidate_route,
)
from xfinaudio.desktop.rendering import format_quality_summary
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan
from xfinaudio.recommendation.strategies import resolve_strategy_name

VariantApplicationBuilder = Callable[..., Any]


class PlanGenerationBuilder(Protocol):
    """Seam that turns candidate records plus UI-derived parameters into a plan.

    The bound colour anchor is keyword-only with a default so the non-colour route
    can forward ``None`` through the same call shape instead of branching on it.
    """

    def __call__(
        self, records: list[Any], request: PrepCopilotGenerationRequest, *, color_anchor_path: str | None = None
    ) -> PrepCopilotPlan: ...


def _internal_strategy_name(combo_value: object) -> str:
    """Normalise whatever the strategy combo yields to an internal strategy name.

    ``currentData()`` is empty for combos populated without user data, so the caller
    falls back to the display label. A display label is not an internal strategy name,
    so handing it to `resolve_candidate_route` would silently skip the colour branch
    and plan the set unanchored. Genuinely unknown text is passed through
    untouched: it already fails downstream in `recommend_playlist`, and raising here
    would turn a deep, reported error into an unhandled one in the UI.
    """
    name = str(combo_value)
    try:
        return resolve_strategy_name(name)
    except ValueError:
        return name


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
        desktop_recommendation_records: RecommendationRecordsRoute,
        desktop_color_anchor_candidate_context: ColorAnchorContextRoute,
        variant_application_builder: VariantApplicationBuilder = build_prep_copilot_variant_application,
        plan_generation_builder: PlanGenerationBuilder = generate_prep_copilot_plan,
    ) -> None:
        self._build_screen = build_screen
        self._build_vm = build_vm
        self._state = state
        self._workflow_service = workflow_service
        self._on_state_changed = on_state_changed
        self._on_status_message = on_status_message
        # Injected rather than reached for through `_state`: the candidate routes are
        # collaborators this controller calls, not window state it reads, and the
        # recommendation service already takes them the same way.
        self._desktop_recommendation_records = desktop_recommendation_records
        self._desktop_color_anchor_candidate_context = desktop_color_anchor_candidate_context
        self._variant_application_builder = variant_application_builder
        self._plan_generation_builder = plan_generation_builder

    def _replace_state(self, updated_state: Any) -> None:
        if hasattr(self._state, "_replace_app_state"):
            self._state._replace_app_state(updated_state)
        else:
            self._state._state = updated_state

    def generate(self) -> None:
        controls = self._state._selected_track_controls()
        if controls is None:
            self._replace_state(apply_prep_copilot_plan_cleared(self._state._state))
            self._build_screen.copilot_table.setRowCount(0)
            self._build_screen.apply_variant_button.setEnabled(False)
            self._on_status_message(self._state.tr("Select at least one complete track before generating Prep Copilot"))
            return
        strategy_combo = self._build_screen.strategy_combo
        strategy_name = _internal_strategy_name(strategy_combo.currentData() or strategy_combo.currentText())
        # A variant that filters the bound anchor away then fails closed instead of
        # rebinding a different one -- see `resolve_candidate_route`.
        records, color_anchor_path = resolve_candidate_route(
            controls,
            strategy_name,
            records_route=self._desktop_recommendation_records,
            color_anchor_context_route=self._desktop_color_anchor_candidate_context,
        )
        genre_focus = self._build_screen.genre_focus_input.text().strip() or None
        request = PrepCopilotGenerationRequest(
            strategy=strategy_name,
            target_track_count=self._build_screen.target_count_input.value(),
            start_path=controls.start_path,
            required_paths=controls.manual_order_paths,
            genre_focus=genre_focus,
        )
        plan = self._plan_generation_builder(records, request, color_anchor_path=color_anchor_path)
        self._replace_state(apply_prep_copilot_plan_generated(self._state._state, plan))
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
        application = self._variant_application_builder(variant)
        recommendation = application.recommendation
        explanation = application.explanation
        quality_report = application.quality_report
        updated_state = apply_prep_copilot_variant(
            self._state._state,
            PrepCopilotVariantApplication(
                recommendation=recommendation,
                explanation=explanation,
                quality_report=quality_report,
                readiness_report=application.readiness_report,
                variant_name=application.variant_name,
            ),
        )
        self._replace_state(updated_state)
        self._on_state_changed()
        self._render_applied_variant_label(application.variant_name)
        self._state.show_recommendation(recommendation.ordered_tracks, recommendation.strategy.name, explanation)
        self._state._review_screen.review_summary_label.setText(format_quality_summary(quality_report))
        self._state._review_screen.dj_readiness_label.setText(
            format_application_dj_readiness_summary(application.readiness_report)
        )
        self._state._populate_dj_readiness_table(application.readiness_report)
        self._state.show_transition_review(explanation)
        self._state._export_screen.export_guidance_label.setText(
            self._state.tr("Inspect the selected Prep Copilot variant before exporting it to Serato.")
        )
        self._on_status_message(self._state.tr("Applied Prep Copilot variant: {0}").format(application.variant_name))

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
