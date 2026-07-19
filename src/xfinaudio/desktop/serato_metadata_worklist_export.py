"""Cohesive extracted export responsibility."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import cast

from xfinaudio.application.serato_metadata_export import (
    export_metadata_status_serato_worklist,
    export_missing_field_serato_worklist,
)
from xfinaudio.desktop.export_dependencies import resolve_export_dependencies
from xfinaudio.desktop.rendering import _missing_worklist_display_name
from xfinaudio.library.models import MetadataStatus

LOGGER = logging.getLogger(__name__)


class SeratoMetadataWorklistExportMixin:
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
            dependencies = resolve_export_dependencies(self)
            result = export_metadata_status_serato_worklist(
                records=records,
                status=cast(MetadataStatus, selected_status),
                serato_folder=serato_folder,
                discover_libraries=dependencies.discover_serato_libraries,
            ).write_result
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
            dependencies = resolve_export_dependencies(self)
            result = export_missing_field_serato_worklist(
                records=records,
                missing_field=missing_field,
                serato_folder=serato_folder,
                discover_libraries=dependencies.discover_serato_libraries,
            ).write_result
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
