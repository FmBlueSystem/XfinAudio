"""View model for the Build Playlist screen.

Transforms AppState into display-ready data for the build screen where the DJ
selects a strategy and launches recommendation or uses Prep Copilot.
No PySide6 dependency — pure Python data transformation.
"""

from __future__ import annotations

from dataclasses import dataclass

from xfinaudio.desktop.app_state import AppState
from xfinaudio.recommendation.strategies import _STRATEGIES


@dataclass(frozen=True)
class StrategyOption:
    name: str
    display_name: str
    description: str
    requires_vibe_metadata: bool


@dataclass(frozen=True)
class CopilotVariantRow:
    index: int
    name: str
    description: str
    track_count: int
    readiness_status: str
    blocker_count: int
    warning_count: int


class BuildViewModel:
    """Transforms AppState into display data for the Build Playlist screen."""

    def available_strategies(self) -> list[StrategyOption]:
        """Return all available strategies as StrategyOption display objects."""
        return [
            StrategyOption(
                name=strategy.name,
                display_name=strategy.display_name,
                description=strategy.description,
                requires_vibe_metadata=strategy.requires_vibe_metadata,
            )
            for strategy in _STRATEGIES.values()
        ]

    def recommend_button_enabled(self, state: AppState) -> bool:
        """True if there are scanned tracks and no operation is in progress."""
        return bool(state.scanned_records) and not state.is_scanning and not state.is_recommending

    def copilot_button_enabled(self, state: AppState) -> bool:
        """True if there are scanned tracks and neither scanning nor recommending."""
        return bool(state.scanned_records) and not state.is_scanning and not state.is_recommending

    def copilot_variants_for_display(self, state: AppState) -> list[CopilotVariantRow]:
        """Return PrepCopilotPlan variants formatted as CopilotVariantRow. Empty list if no plan."""
        if state.last_prep_copilot_plan is None:
            return []
        return [
            CopilotVariantRow(
                index=i,
                name=variant.name,
                description=variant.description,
                track_count=len(variant.recommendation.ordered_tracks),
                readiness_status=variant.readiness.status,
                blocker_count=len(variant.blockers),
                warning_count=len(variant.warnings),
            )
            for i, variant in enumerate(state.last_prep_copilot_plan.variants)
        ]

    def applied_variant_label(self, state: AppState) -> str:
        """Return display label for the applied variant, or empty string if none."""
        if state.applied_variant_name is None:
            return ""
        return f"Active: {state.applied_variant_name.capitalize()}"

    def can_proceed(self, state: AppState) -> bool:
        """True if a recommendation has been generated (enables 'Review →' CTA)."""
        return state.last_recommendation is not None


__all__ = [
    "BuildViewModel",
    "CopilotVariantRow",
    "StrategyOption",
]
