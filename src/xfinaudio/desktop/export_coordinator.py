"""Export coordination logic: pure planning helpers plus a Qt-aware orchestrator.

The free functions stay pure and independently testable. ``ExportCoordinator``
is the stateful, Qt-aware orchestrator extracted from ``MainWindow``; it reads
state and widgets through a ``host`` handle (the ``MainWindow``) and calls the
free functions internally.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

from xfinaudio.desktop.rendering import _missing_worklist_display_name, _table_item
from xfinaudio.desktop.table_populators import populate_serato_export_history_table
from xfinaudio.desktop.theme import _READINESS_STATUS_LABELS
from xfinaudio.exporting.playlist_file_export import plan_playlist_file_export
from xfinaudio.exporting.rekordbox_xml import write_rekordbox_playlist_xml
from xfinaudio.exporting.serato_crate import write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    SeratoLibraryNotFoundError,
    discover_serato_libraries,
    plan_copilot_variant_serato_playlist_export,
    plan_generated_serato_playlist_export,
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    plan_serato_playlist_export,
    select_serato_library_for_tracks,
)
from xfinaudio.exporting.traktor_nml import write_traktor_playlist_nml
from xfinaudio.exporting.virtualdj_xml import write_virtualdj_playlist_xml
from xfinaudio.library.models import MetadataStatus
from xfinaudio.quality.dj_readiness import DjReadinessReport, write_dj_readiness_report
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

LOGGER = logging.getLogger(__name__)

_SERATO_EXPORT_HISTORY_LIMIT = 5


class ExportHost(Protocol):
    """Structural host boundary for ``ExportCoordinator``.

    Declares only the ``MainWindow`` members the coordinator reads or calls,
    decoupling export orchestration from the concrete window type.
    """

    last_recommendation: PlaylistRecommendation | None
    last_dj_readiness_report: DjReadinessReport | None
    last_quality_report: Any | None
    settings: Any
    applied_prep_copilot_variant_name: str | None
    status_label: Any
    serato_export_history: list[dict]
    _export_screen: Any

    def tr(self, text: str) -> str: ...
    def _sync_state(self) -> None: ...
    def _show_dj_readiness(
        self,
        recommendation: PlaylistRecommendation,
        quality_report: Any,
        *,
        serato_plan: Any,
        serato_volume_root: Any,
    ) -> None: ...
    def _selected_missing_metadata_filter(self) -> str | None: ...
    def _selected_metadata_status_filter(self) -> str | None: ...
    def _metadata_status_records(self, status: str) -> list[Any]: ...
    def _metadata_missing_field_records(self, field: str) -> list[Any]: ...


def plan_serato_export(
    recommendation: PlaylistRecommendation,
    copilot_variant_name: str | None,
    *,
    serato_folder: Path | None = None,
    crate_name: str | None = None,
    generated_at: datetime | None = None,
) -> tuple[Any, SeratoLibrary]:
    """Build a Serato export plan without writing it.

    Selects the appropriate planning strategy based on whether a crate_name or
    copilot_variant_name is provided, falling back to a generated strategy name.
    """
    library = (
        SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
        if serato_folder is not None
        else select_serato_library_for_tracks(
            [track.path for track in recommendation.ordered_tracks],
            discover_serato_libraries(),
        )
    )
    if crate_name is not None:
        plan = plan_serato_playlist_export(crate_name, recommendation, library)
    elif copilot_variant_name is not None:
        plan = plan_copilot_variant_serato_playlist_export(
            copilot_variant_name,
            recommendation,
            library,
            generated_at=generated_at,
        )
    else:
        plan = plan_generated_serato_playlist_export(
            recommendation,
            library,
            generated_at=generated_at,
        )
    return plan, library


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
) -> tuple[Path, Path]:
    """Write DJ Readiness JSON/CSV sidecars to safe_folder (or next to the crate as fallback)."""
    base = safe_folder if safe_folder is not None else crate_path.parent
    base.mkdir(parents=True, exist_ok=True)
    stem = crate_path.stem
    json_path = base / f"{stem}.dj-readiness.json"
    csv_path = base / f"{stem}.dj-readiness.csv"
    return write_dj_readiness_report(report, json_path, csv_path)


class ExportCoordinator:
    """Qt-aware export orchestration extracted from MainWindow (first slice).

    State and widget access flow through ``host`` (the ``MainWindow``); pure
    planning is delegated to the module-level free functions.
    """

    def __init__(self, host: ExportHost, on_export_success: Callable[[], None] | None = None) -> None:
        self._host = host
        self._on_export_success = on_export_success

    def selected_software(self) -> str:
        """Return the currently selected DJ software from the Export screen."""
        return self._host._export_screen.software_selector.currentText()

    def preview_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Preview the export destination for the selected DJ software."""
        host = self._host
        software = self.selected_software()
        if software == "Serato":
            self.preview_serato_export(serato_folder=serato_folder, crate_name=crate_name, generated_at=generated_at)
            return

        if host.last_recommendation is None:
            host.status_label.setText(
                host.tr("Generate a recommendation before previewing {0} export").format(software)
            )
            return

        safe_folder = host.settings.export.safe_export_folder
        if safe_folder is None:
            host.status_label.setText(
                host.tr("Choose a safe export folder before previewing {0} export").format(software)
            )
            return

        try:
            plan = plan_playlist_file_export(
                software=software,
                recommendation=host.last_recommendation,
                safe_folder=safe_folder,
                requested_name=crate_name,
                variant_name=host.applied_prep_copilot_variant_name,
                generated_at=generated_at,
            )
        except ValueError:
            host.status_label.setText(host.tr("Unknown export software: {0}").format(software))
            return

        host._export_screen.export_guidance_label.setText(
            host.tr("{0} export preview: {1} | Tracks: {2}").format(
                software, plan.target_path, len(host.last_recommendation.ordered_tracks)
            )
        )
        host.status_label.setText(host.tr("{0} export preview: {1}").format(software, plan.target_path))

    def export_recommendation(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Export the current recommendation to the selected DJ software."""
        host = self._host
        software = self.selected_software()
        if software == "Serato":
            self.export_recommendation_to_serato(
                serato_folder=serato_folder, crate_name=crate_name, generated_at=generated_at
            )
            return

        if host.last_recommendation is None:
            host.status_label.setText(host.tr("Generate a recommendation before exporting to {0}").format(software))
            return
        if host.last_dj_readiness_report is not None and host.last_dj_readiness_report.status == "blocked":
            host.status_label.setText(host.tr("Resolve blocked readiness checks before exporting."))
            return

        safe_folder = host.settings.export.safe_export_folder
        if safe_folder is None:
            host.status_label.setText(host.tr("Choose a safe export folder before exporting to {0}").format(software))
            return

        try:
            plan = plan_playlist_file_export(
                software=software,
                recommendation=host.last_recommendation,
                safe_folder=safe_folder,
                requested_name=crate_name,
                variant_name=host.applied_prep_copilot_variant_name,
                generated_at=generated_at,
            )
        except ValueError:
            host.status_label.setText(host.tr("Unknown export software: {0}").format(software))
            return

        try:
            if software == "Rekordbox":
                written = write_rekordbox_playlist_xml(
                    host.last_recommendation,
                    plan.target_path,
                    playlist_name=plan.playlist_name,
                )
            elif software == "Traktor":
                written = write_traktor_playlist_nml(
                    host.last_recommendation,
                    plan.target_path,
                    playlist_name=plan.playlist_name,
                )
            elif software == "VirtualDJ":
                written = write_virtualdj_playlist_xml(
                    host.last_recommendation,
                    plan.target_path,
                    playlist_name=plan.playlist_name,
                )
            else:
                host.status_label.setText(host.tr("Unknown export software: {0}").format(software))
                return
        except Exception as exc:
            LOGGER.exception("%s export failed", software)
            host.status_label.setText(host.tr("{0} export failed: {1}").format(software, exc))
            return

        host._export_screen.export_guidance_label.setText(
            host.tr("{0} playlist exported: {1}. Import it into {0}.").format(software, written)
        )
        host.status_label.setText(host.tr("Exported {0} playlist: {1}").format(software, written))

    def preview_serato_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Preview the Serato crate destination without writing files."""
        host = self._host
        if host.last_recommendation is None:
            host.status_label.setText(host.tr("Generate a recommendation before previewing Serato export"))
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
        if host.last_recommendation is None:
            host.status_label.setText(host.tr("Generate a recommendation before exporting to Serato"))
            return
        if host.last_dj_readiness_report is not None and host.last_dj_readiness_report.status == "blocked":
            host.status_label.setText(host.tr("Resolve blocked readiness checks before exporting."))
            return

        try:
            plan, library = self._plan_current_serato_export(
                serato_folder=serato_folder,
                crate_name=crate_name,
                generated_at=generated_at,
            )
            result = write_serato_crate(plan, confirm=True)
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
                host.last_recommendation,
                host.last_quality_report,
                serato_plan=plan,
                serato_volume_root=library.volume_root,
            )
        if host.last_dj_readiness_report is not None:
            safe_folder = host.settings.export.safe_export_folder
            try:
                json_path, csv_path = write_readiness_sidecars(
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
        )

    def export_metadata_status_to_serato(
        self,
        *,
        status: str | None = None,
        missing_field: str | None = None,
        serato_folder: Path | None = None,
    ) -> None:
        """Export complete or incomplete metadata worklists as Serato crates."""
        host = self._host
        selected_missing_field = missing_field or host._selected_missing_metadata_filter()
        selected_status = status or host._selected_metadata_status_filter()
        if selected_missing_field is not None:
            self._export_missing_metadata_worklist_to_serato(selected_missing_field, serato_folder=serato_folder)
            return

        if selected_status not in {"complete", "incomplete"}:
            host.status_label.setText(host.tr("Choose Complete or Incomplete before exporting a metadata worklist"))
            return

        records = host._metadata_status_records(selected_status)
        if not records:
            host.status_label.setText(
                host.tr("No {0} tracks are available for metadata export").format(selected_status)
            )
            return

        try:
            library = (
                SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
                if serato_folder is not None
                else select_serato_library_for_tracks(
                    [record.path for record in records],
                    discover_serato_libraries(),
                )
            )
            plan = plan_metadata_status_serato_export(records, cast(MetadataStatus, selected_status), library)
            result = write_serato_crate(plan, confirm=True)
        except Exception as exc:
            LOGGER.exception("Serato metadata status export failed")
            host.status_label.setText(host.tr("Serato metadata export failed: {0}").format(exc))
            return

        host._export_screen.export_guidance_label.setText(
            host.tr(
                "Metadata worklist exported: {0}. Complete missing metadata in Serato, then choose the same folder "
                "and click Scan Metadata to refresh XfinAudio."
            ).format(result.written_path)
        )
        host.status_label.setText(
            host.tr("Exported {0} metadata crate: {1}").format(selected_status, result.written_path)
        )

    def _export_missing_metadata_worklist_to_serato(
        self,
        missing_field: str,
        *,
        serato_folder: Path | None = None,
    ) -> None:
        """Export a specific missing-field metadata worklist as a Serato crate."""
        host = self._host
        records = host._metadata_missing_field_records(missing_field)
        display_field = _missing_worklist_display_name(missing_field)
        if not records:
            host.status_label.setText(host.tr("No tracks are missing {0} for metadata export").format(display_field))
            return

        try:
            library = (
                SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
                if serato_folder is not None
                else select_serato_library_for_tracks(
                    [record.path for record in records],
                    discover_serato_libraries(),
                )
            )
            plan = plan_metadata_missing_field_serato_export(records, missing_field, library)
            result = write_serato_crate(plan, confirm=True)
        except Exception as exc:
            LOGGER.exception("Serato missing-metadata export failed")
            host.status_label.setText(host.tr("Serato metadata export failed: {0}").format(exc))
            return

        host._export_screen.export_guidance_label.setText(
            host.tr(
                "Metadata worklist exported: {0}. Complete missing metadata in Serato, then click Scan Metadata in "
                "XfinAudio to refresh."
            ).format(result.written_path)
        )
        host.status_label.setText(
            host.tr("Exported Missing {0} metadata crate: {1}").format(display_field, result.written_path)
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
