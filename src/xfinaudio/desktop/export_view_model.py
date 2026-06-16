"""ExportViewModel — transforms AppState into display data for the Export screen."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication

from xfinaudio.desktop.app_state import AppState

_VARIANT_LABELS: dict[str, str] = {
    "safe": QCoreApplication.translate("ExportViewModel", "Variant: Safe"),
    "balanced": QCoreApplication.translate("ExportViewModel", "Variant: Balanced"),
    "adventurous": QCoreApplication.translate("ExportViewModel", "Variant: Adventurous"),
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
        """True if export is permitted, via the shared `export_allowed` predicate.

        A recommendation must exist with at least one non-removed track, and any present readiness
        report must not be blocked (missing report → allowed).
        """
        from xfinaudio.desktop.navigation_controller import export_allowed

        return export_allowed(state)

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
        text = QCoreApplication.translate("ExportViewModel", "{0} tracks → {1}").format(track_count, strategy_name)

        variant = state.applied_variant_name
        if variant is not None:
            text += QCoreApplication.translate("ExportViewModel", " (variant: {0})").format(variant)

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
                track_count_str = QCoreApplication.translate("ExportViewModel", "{0} tracks").format(int(raw_tracks))
            except (ValueError, TypeError):
                track_count_str = QCoreApplication.translate("ExportViewModel", "{0} tracks").format(raw_tracks)

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
            return QCoreApplication.translate("ExportViewModel", "Direct Recommend")
        return _VARIANT_LABELS.get(
            variant,
            QCoreApplication.translate("ExportViewModel", "Variant: {0}").format(variant.capitalize()),
        )

    def safe_folder_label(self, state: AppState) -> str:
        """Display label for the configured safe export folder."""
        folder = state.settings.export.safe_export_folder
        if folder is None:
            return QCoreApplication.translate("ExportViewModel", "No safe folder set")
        return folder.name

    def track_count_text(self, state: AppState) -> str:
        """Track count display text. Returns '—' when no recommendation exists."""
        rec = state.last_recommendation
        if rec is None:
            return "—"
        return QCoreApplication.translate("ExportViewModel", "{0} tracks").format(len(rec.ordered_tracks))

    def empty_state_text(self, state: AppState) -> str:
        """Human-readable guidance when no recommendation is available for export."""
        if state.last_recommendation is not None:
            return ""
        return QCoreApplication.translate(
            "ExportViewModel",
            "Build a playlist first to see export options. "
            "Live Serato writes are not part of the verified release candidate; "
            "back up your library before copying any crate to a live _Serato_ folder. "
            "Preview shows crate contents without writing files. "
            "Exports are written to the configured safe export folder, not directly to a live Serato library.",
        )

    def preview_explanation_text(self) -> str:
        """Explain that preview does not write files."""
        return QCoreApplication.translate(
            "ExportViewModel",
            "Preview shows the planned crate contents without writing any files.",
        )

    def destination_text(self) -> str:
        """Explain the destination format."""
        return QCoreApplication.translate(
            "ExportViewModel",
            "Exports are written to the configured safe export folder; "
            "copy files to a live _Serato_/Subcrates folder only after backup and manual verification.",
        )
