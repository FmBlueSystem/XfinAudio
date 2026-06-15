"""Central mutable state container for the XfinAudio desktop application."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, get_args

from xfinaudio.config.settings import AppSettings
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan

ScreenName = Literal["library", "build", "review", "export", "metadata"]

VALID_SCREENS: frozenset[str] = frozenset(get_args(ScreenName))


@dataclass
class AppState:
    # Library / Scan
    selected_folder: Path | None = None
    scanned_records: list[TrackRecord] = field(default_factory=list)
    records_by_path: dict[str, TrackRecord] = field(default_factory=dict)

    # Recommendation
    last_recommendation: PlaylistRecommendation | None = None
    last_playlist_explanation: PlaylistExplanation | None = None
    last_quality_report: RecommendationQualityReport | None = None
    last_dj_readiness_report: DjReadinessReport | None = None

    # Prep Copilot
    last_prep_copilot_plan: PrepCopilotPlan | None = None
    applied_variant_name: Literal["safe", "balanced", "adventurous"] | None = None

    # Export
    serato_export_history: list[dict] = field(default_factory=list)

    # Settings
    settings: AppSettings = field(default_factory=AppSettings)

    # Track constraints
    excluded_paths: frozenset[str] = field(default_factory=frozenset)
    locked_paths: frozenset[str] = field(default_factory=frozenset)
    playlist_removed_paths: frozenset[str] = field(default_factory=frozenset)

    # Selection
    selected_library_paths: list[str] = field(default_factory=list)

    # Navigation
    current_screen: ScreenName = "library"

    # Transient scan state (not persisted)
    is_scanning: bool = False
    is_recommending: bool = False
    scan_progress_count: int = 0
    scan_progress_total: int = 0
    scan_elapsed_seconds: float = 0.0
    recommend_progress_count: int = 0
    recommend_progress_total: int = 0
    recommend_elapsed_seconds: float = 0.0
    is_exporting: bool = False
    export_progress_count: int = 0
    export_progress_total: int = 0
    export_elapsed_seconds: float = 0.0
    is_completing_spectral: bool = False
    spectral_progress_count: int = 0
    spectral_total_count: int = 0

    def model_copy(self, *, update: dict[str, object] | None = None) -> AppState:
        """Return a shallow copy with selected fields replaced."""
        state = copy.copy(self)
        if update is not None:
            for key, value in update.items():
                setattr(state, key, value)
        return state

    def with_screen(self, screen: ScreenName) -> AppState:
        s = copy.copy(self)
        s.serato_export_history = list(self.serato_export_history)
        s.current_screen = screen
        return s

    def with_scanned_records(self, records: list[TrackRecord]) -> AppState:
        s = copy.copy(self)
        s.scanned_records = list(records)
        s.records_by_path = {r.path: r for r in records}
        return s

    def debug_summary(self) -> dict[str, object]:
        return {
            "screen": self.current_screen,
            "folder": str(self.selected_folder),
            "tracks": len(self.scanned_records),
            "has_recommendation": self.last_recommendation is not None,
            "has_readiness": self.last_dj_readiness_report is not None,
            "applied_variant": self.applied_variant_name,
            "export_history": len(self.serato_export_history),
        }
