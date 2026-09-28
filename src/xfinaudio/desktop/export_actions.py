"""Thin export action facade for MainWindow."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog

from xfinaudio.application.dj_readiness import write_application_dj_readiness_report
from xfinaudio.config.settings import ExportSettings
from xfinaudio.metadata.metadata_gaps import (
    build_metadata_gap_report,
    export_metadata_gap_report_csv,
    export_metadata_gap_report_json,
)


class ExportActions:
    def __init__(self, export_coordinator: Any) -> None:
        self._export_coordinator = export_coordinator

    @property
    def _host(self) -> Any:
        return self._export_coordinator._host

    def choose_safe_export_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self._host, self._host.tr("Choose safe export folder"))
        if folder:
            self.set_safe_export_folder(Path(folder))

    def set_safe_export_folder(self, folder: Path) -> None:
        host = self._host
        if host.selected_folder is not None and folder == host.selected_folder:
            host.status_label.setText(host.tr("Safe export folder must be outside the selected audio folder"))
            return
        host.settings = host.settings.model_copy(update={"export": ExportSettings(safe_export_folder=folder)})
        if host.settings_repository is not None:
            host.settings_repository.save(host.settings)
        host._export_screen.safe_export_folder_label.setText(
            host._settings_controller.format_safe_export_folder_label()
        )
        host.status_label.setText(host.tr("Safe export folder selected"))
        host._sync_state()

    def export_dj_readiness_report(self, *, generated_at: datetime | None = None) -> None:
        host = self._host
        if host.last_dj_readiness_report is None:
            host.status_label.setText(host.tr("Generate a recommendation before exporting DJ readiness"))
            return
        safe_folder = host.settings.export.safe_export_folder
        if safe_folder is None:
            host.status_label.setText(host.tr("Choose a safe export folder before exporting DJ readiness"))
            return
        generated_at = generated_at or datetime.now()
        timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
        json_path = safe_folder / f"xfinaudio-dj-readiness-{timestamp}.json"
        csv_path = safe_folder / f"xfinaudio-dj-readiness-{timestamp}.csv"
        json_path, csv_path = write_application_dj_readiness_report(host.last_dj_readiness_report, json_path, csv_path)
        host.status_label.setText(host.tr("Exported DJ readiness report: {0} and {1}").format(json_path, csv_path))

    def export_metadata_gap_report(self, *, generated_at: datetime | None = None) -> None:
        """Write the deterministic metadata gap report as JSON and CSV.

        Mirrors ``export_dj_readiness_report``: guard on nothing to export and on
        a missing safe folder, then write both files with a timestamped,
        deterministic filename. The report itself comes from the pure domain
        function over the currently scanned records; the export never decides
        which tracks are gaps.
        """
        host = self._host
        report = build_metadata_gap_report(host.scanned_records)
        if report.incomplete_count == 0:
            host.status_label.setText(host.tr("Scan a library with metadata gaps before exporting the gap report"))
            return
        safe_folder = host.settings.export.safe_export_folder
        if safe_folder is None:
            host.status_label.setText(host.tr("Choose a safe export folder before exporting the gap report"))
            return
        generated_at = generated_at or datetime.now()
        timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
        json_path = safe_folder / f"xfinaudio-metadata-gaps-{timestamp}.json"
        csv_path = safe_folder / f"xfinaudio-metadata-gaps-{timestamp}.csv"
        json_path.write_text(export_metadata_gap_report_json(report), encoding="utf-8")
        csv_path.write_text(export_metadata_gap_report_csv(report), encoding="utf-8")
        host.status_label.setText(host.tr("Exported metadata gap report: {0} and {1}").format(json_path, csv_path))

    def preview_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        self._export_coordinator.preview_export(
            serato_folder=serato_folder,
            crate_name=crate_name,
            generated_at=generated_at,
        )

    def export_recommendation(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        self._export_coordinator.export_recommendation(
            serato_folder=serato_folder,
            crate_name=crate_name,
            generated_at=generated_at,
        )

    def preview_serato_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        self._export_coordinator.preview_serato_export(
            serato_folder=serato_folder,
            crate_name=crate_name,
            generated_at=generated_at,
        )

    def export_recommendation_to_serato(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        self._export_coordinator.export_recommendation_to_serato(
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
        self._export_coordinator.export_metadata_status_to_serato(
            status=status,
            missing_field=missing_field,
            serato_folder=serato_folder,
        )
