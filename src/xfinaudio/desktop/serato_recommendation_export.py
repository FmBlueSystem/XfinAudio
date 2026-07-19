"""Cohesive extracted export responsibility."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from xfinaudio.application.dj_readiness import write_application_dj_readiness_report
from xfinaudio.application.serato_playlist_export import preview_serato_playlist_export
from xfinaudio.desktop.export_dependencies import resolve_export_dependencies
from xfinaudio.desktop.rendering import _table_item
from xfinaudio.desktop.table_populators import populate_serato_export_history_table
from xfinaudio.desktop.theme import _READINESS_STATUS_LABELS
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    SeratoLibraryNotFoundError,
    discover_serato_libraries,
)
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

LOGGER = logging.getLogger(__name__)
_SERATO_EXPORT_HISTORY_LIMIT = 5


def plan_serato_export(
    recommendation: PlaylistRecommendation,
    copilot_variant_name: str | None,
    *,
    serato_folder: Path | None = None,
    crate_name: str | None = None,
    generated_at: datetime | None = None,
    discover_libraries=discover_serato_libraries,
) -> tuple[Any, SeratoLibrary]:
    """Build a Serato export plan without writing it.

    Selects the appropriate planning strategy based on whether a crate_name or
    copilot_variant_name is provided, falling back to a generated strategy name.
    """
    preview = preview_serato_playlist_export(
        recommendation=recommendation,
        copilot_variant_name=copilot_variant_name,
        serato_folder=serato_folder,
        crate_name=crate_name,
        generated_at=generated_at,
        discover_libraries=discover_libraries,
    )
    return preview.plan, preview.library


def build_serato_export_entry(
    recommendation: PlaylistRecommendation,
    written_path: Path,
    *,
    readiness_json_path: Path | None = None,
    readiness_csv_path: Path | None = None,
) -> dict[str, str]:
    """Build a Serato export receipt dict from a completed export."""
    return {
        "time": datetime.now().strftime("%H:%M:%S"),
        "strategy": recommendation.strategy.name,
        "tracks": str(len(recommendation.ordered_tracks)),
        "path": str(written_path),
        "readiness_json_path": "" if readiness_json_path is None else str(readiness_json_path),
        "readiness_csv_path": "" if readiness_csv_path is None else str(readiness_csv_path),
    }


def record_export(
    history: list[dict],
    entry: dict,
    max_entries: int = 5,
) -> list[dict]:
    """Return a new history list with entry prepended and truncated to max_entries."""
    return [entry, *history][:max_entries]


def write_readiness_sidecars(
    report: DjReadinessReport,
    crate_path: Path,
    *,
    safe_folder: Path | None = None,
    write_report=write_application_dj_readiness_report,
) -> tuple[Path, Path]:
    """Write DJ Readiness JSON/CSV sidecars to safe_folder (or next to the crate as fallback)."""
    base = safe_folder if safe_folder is not None else crate_path.parent
    base.mkdir(parents=True, exist_ok=True)
    stem = crate_path.stem
    json_path = base / f"{stem}.dj-readiness.json"
    csv_path = base / f"{stem}.dj-readiness.csv"
    return write_report(report, json_path, csv_path)


class SeratoRecommendationExportMixin:
    def preview_serato_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Preview the Serato crate destination without writing files."""
        host = self._host
        dependencies = resolve_export_dependencies(self)
        decision = dependencies.evaluate_export_gate(self._build_export_gate_request("preview", "Serato"))
        if self._handle_denied_export_gate(decision, "preview", "Serato"):
            return

        try:
            plan, _library = self._plan_current_serato_export(
                serato_folder=serato_folder,
                crate_name=crate_name,
                generated_at=generated_at,
            )
        except SeratoLibraryNotFoundError:
            host.status_label.setText(
                host.tr("Serato not found — open Serato DJ Pro at least once to create its library folder")
            )
            return
        except Exception as exc:
            LOGGER.exception("Serato export preview failed")
            host.status_label.setText(host.tr("Serato export preview failed: {0}").format(exc))
            return

        variant = host.applied_prep_copilot_variant_name or "none"
        readiness = (
            _READINESS_STATUS_LABELS[host.last_dj_readiness_report.status]
            if host.last_dj_readiness_report is not None
            else host.tr("Not available")
        )
        will_write = host.tr("yes") if not plan.target_path.exists() else host.tr("replace with backup")
        host._export_screen.export_guidance_label.setText(
            host.tr(
                "Serato export preview: {0} | Variant: {1} | Tracks: {2} | Will write: {3} | Readiness: {4}"
            ).format(plan.target_path, variant, len(plan.relative_paths), will_write, readiness)
        )
        host.status_label.setText(host.tr("Serato export preview: {0}").format(plan.target_path))

    def export_recommendation_to_serato(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Export the current recommendation as a confirmed Serato crate."""
        host = self._host
        dependencies = resolve_export_dependencies(self)
        decision = dependencies.evaluate_export_gate(self._build_export_gate_request("export", "Serato"))
        if self._handle_denied_export_gate(decision, "export", "Serato"):
            return
        recommendation = host.last_recommendation
        assert recommendation is not None

        try:
            export_result = dependencies.export_serato_playlist(
                recommendation=recommendation,
                copilot_variant_name=host.applied_prep_copilot_variant_name,
                serato_folder=serato_folder,
                crate_name=crate_name,
                generated_at=generated_at,
                discover_libraries=dependencies.discover_serato_libraries,
            )
            plan = export_result.plan
            library = export_result.library
            result = export_result.write_result
        except SeratoLibraryNotFoundError:
            host.status_label.setText(
                host.tr("Serato not found — open Serato DJ Pro at least once to create its library folder")
            )
            return
        except Exception as exc:
            LOGGER.exception("Serato export failed")
            host.status_label.setText(host.tr("Serato export failed: {0}").format(exc))
            return

        backup_note = (
            host.tr(" Backup: {0}").format(result.backup_path)
            if result.backup_path is not None
            else host.tr(" No previous crate existed.")
        )
        readiness_note = ""
        readiness_paths: tuple[Path | None, Path | None] = (None, None)
        if host.last_quality_report is not None:
            host._show_dj_readiness(
                recommendation,
                host.last_quality_report,
                serato_plan=plan,
                serato_volume_root=library.volume_root,
            )
        if host.last_dj_readiness_report is not None:
            safe_folder = host.settings.export.safe_export_folder
            try:
                json_path, csv_path = dependencies.write_readiness_sidecars(
                    host.last_dj_readiness_report, result.written_path, safe_folder=safe_folder
                )
            except OSError as exc:
                LOGGER.exception("Serato readiness sidecar export failed")
                readiness_note = host.tr(" Readiness report failed: {0}.").format(exc)
            else:
                readiness_paths = (json_path, csv_path)
                readiness_note = host.tr(" Readiness reports: {0} and {1}.").format(json_path, csv_path)
        host._export_screen.export_guidance_label.setText(
            host.tr("Serato crate exported: {0}. Open Serato DJ Pro and check the crate under Subcrates.").format(
                result.written_path
            )
            + backup_note
            + readiness_note
        )
        status_text = host.tr("Exported Serato crate: {0}").format(result.written_path)
        if readiness_paths == (None, None) and host.last_dj_readiness_report is not None and readiness_note:
            status_text = f"{status_text};{readiness_note}"
        host.status_label.setText(status_text)
        self._record_serato_export(
            result.written_path, readiness_json_path=readiness_paths[0], readiness_csv_path=readiness_paths[1]
        )
        if self._on_export_success is not None and not (
            host.last_dj_readiness_report is not None and readiness_paths == (None, None) and readiness_note
        ):
            self._on_export_success()

    def _plan_current_serato_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> tuple[Any, SeratoLibrary]:
        """Build the current Serato export plan without writing it."""
        host = self._host
        if host.last_recommendation is None:
            raise ValueError("Generate a recommendation before planning Serato export")
        return plan_serato_export(
            host.last_recommendation,
            host.applied_prep_copilot_variant_name,
            serato_folder=serato_folder,
            crate_name=crate_name,
            generated_at=generated_at,
            discover_libraries=resolve_export_dependencies(self).discover_serato_libraries,
        )

    def _record_serato_export(
        self,
        written_path: Path,
        *,
        readiness_json_path: Path | None = None,
        readiness_csv_path: Path | None = None,
    ) -> None:
        """Record a bounded in-session Serato export receipt for user verification."""
        host = self._host
        if host.last_recommendation is None:
            return
        entry = build_serato_export_entry(
            host.last_recommendation,
            written_path,
            readiness_json_path=readiness_json_path,
            readiness_csv_path=readiness_csv_path,
        )
        host.serato_export_history = record_export(host.serato_export_history, entry, _SERATO_EXPORT_HISTORY_LIMIT)
        host._sync_state()
        self._render_serato_export_history()

    def _render_serato_export_history(self) -> None:
        """Render recent Serato export receipts without crowding the desktop layout."""
        host = self._host
        host._export_screen.history_table.setVisible(bool(host.serato_export_history))
        populate_serato_export_history_table(
            host._export_screen.history_table,
            host.serato_export_history,
            item_factory=_table_item,
        )
