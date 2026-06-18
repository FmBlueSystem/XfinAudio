"""Thin export action facade for MainWindow."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog

from xfinaudio.config.settings import ExportSettings
from xfinaudio.quality.dj_readiness import write_dj_readiness_report


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
        json_path, csv_path = write_dj_readiness_report(host.last_dj_readiness_report, json_path, csv_path)
        host.status_label.setText(host.tr("Exported DJ readiness report: {0} and {1}").format(json_path, csv_path))

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
