"""ExportViewModel — transforms AppState into display data for the Export screen."""

from __future__ import annotations

from dataclasses import dataclass

from xfinaudio.desktop.app_state import AppState

_VARIANT_LABELS: dict[str, str] = {
    "safe": "Variant: Safe",
    "balanced": "Variant: Balanced",
    "adventurous": "Variant: Adventurous",
}


@dataclass(frozen=True)
class ExportHistoryRow:
    crate_name: str
    destination: str
    track_count: str
    exported_at: str
    readiness: str


class ExportViewModel:
    """Pure data transformer: AppState → export screen display values. No PySide6."""

    def export_readiness_enabled(self, state: AppState) -> bool:
        """True only when a readiness report exists AND a safe folder is configured."""
        return state.last_dj_readiness_report is not None and state.settings.export.safe_export_folder is not None

    def export_enabled(self, state: AppState) -> bool:
        """True if a recommendation exists and readiness is not blocked.

        If no readiness report is present, export is allowed (no info → no block).
        """
        if state.last_recommendation is None:
            return False
        report = state.last_dj_readiness_report
        return not (report is not None and report.status == "blocked")

    def preview_text(self, state: AppState) -> str | None:
        """Human-readable description of what will be exported.

        Returns None when there is no recommendation.
        Format: '{N} tracks → {strategy_name}' with optional ' (variant: {name})'.
        """
        rec = state.last_recommendation
        if rec is None:
            return None

        track_count = len(rec.ordered_tracks)
        strategy_name = rec.strategy.name
        text = f"{track_count} tracks → {strategy_name}"

        variant = state.applied_variant_name
        if variant is not None:
            text += f" (variant: {variant})"

        return text

    def export_history_rows(self, state: AppState) -> list[ExportHistoryRow]:
        """Map serato_export_history to ExportHistoryRow. Most recent first.

        History is already stored most-recent-first by record_export, so order
        is preserved as-is.
        """
        rows: list[ExportHistoryRow] = []
        for entry in state.serato_export_history:
            raw_tracks = entry.get("tracks", "0")
            try:
                track_count_str = f"{int(raw_tracks)} tracks"
            except (ValueError, TypeError):
                track_count_str = f"{raw_tracks} tracks"

            rows.append(
                ExportHistoryRow(
                    crate_name=entry.get("strategy", ""),
                    destination=entry.get("path", ""),
                    track_count=track_count_str,
                    exported_at=entry.get("time", ""),
                    readiness="—",
                )
            )
        return rows

    def applied_variant_label(self, state: AppState) -> str:
        """Human-readable label for the applied prep-copilot variant."""
        variant = state.applied_variant_name
        if variant is None:
            return "Direct Recommend"
        return _VARIANT_LABELS.get(variant, f"Variant: {variant.capitalize()}")

    def safe_folder_label(self, state: AppState) -> str:
        """Display label for the configured safe export folder."""
        folder = state.settings.export.safe_export_folder
        if folder is None:
            return "No safe folder set"
        return folder.name

    def track_count_text(self, state: AppState) -> str:
        """Track count display text. Returns '—' when no recommendation exists."""
        rec = state.last_recommendation
        if rec is None:
            return "—"
        return f"{len(rec.ordered_tracks)} tracks"
