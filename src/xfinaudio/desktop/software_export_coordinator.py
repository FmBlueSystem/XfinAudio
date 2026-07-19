"""Cohesive extracted export responsibility."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from xfinaudio.application.playlist_file_export import export_playlist_file, preview_playlist_file_export
from xfinaudio.exporting.export_readiness import evaluate_export_gate

LOGGER = logging.getLogger(__name__)


def _dependencies(owner: Any) -> Any:
    resolver = getattr(owner, "_export_dependencies", None)
    if resolver is not None:
        return resolver()
    return type(
        "SoftwareExportDependencies",
        (),
        {
            "evaluate_export_gate": staticmethod(evaluate_export_gate),
            "preview_playlist_file_export": staticmethod(preview_playlist_file_export),
            "export_playlist_file": staticmethod(export_playlist_file),
        },
    )()


class SoftwareExportCoordinatorMixin:
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

        dependencies = _dependencies(self)
        decision = dependencies.evaluate_export_gate(self._build_export_gate_request("preview", software))
        if self._handle_denied_export_gate(decision, "preview", software):
            return

        recommendation = host.last_recommendation
        safe_folder = host.settings.export.safe_export_folder
        assert recommendation is not None
        assert safe_folder is not None

        try:
            plan = dependencies.preview_playlist_file_export(
                software=software,
                recommendation=recommendation,
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
                software, plan.target_path, len(recommendation.ordered_tracks)
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

        dependencies = _dependencies(self)
        decision = dependencies.evaluate_export_gate(self._build_export_gate_request("export", software))
        if self._handle_denied_export_gate(decision, "export", software):
            return

        recommendation = host.last_recommendation
        safe_folder = host.settings.export.safe_export_folder
        assert recommendation is not None
        assert safe_folder is not None

        try:
            result = dependencies.export_playlist_file(
                software=software,
                recommendation=recommendation,
                safe_folder=safe_folder,
                requested_name=crate_name,
                variant_name=host.applied_prep_copilot_variant_name,
                generated_at=generated_at,
            )
        except ValueError:
            host.status_label.setText(host.tr("Unknown export software: {0}").format(software))
            return
        except Exception as exc:
            LOGGER.exception("%s export failed", software)
            host.status_label.setText(host.tr("{0} export failed: {1}").format(software, exc))
            return

        written = result.written_path
        host._export_screen.export_guidance_label.setText(
            host.tr("{0} playlist exported: {1}. Import it into {0}.").format(software, written)
        )
        host.status_label.setText(host.tr("Exported {0} playlist: {1}").format(software, written))
