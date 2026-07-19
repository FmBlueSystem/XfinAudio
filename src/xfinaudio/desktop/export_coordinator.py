"""Export coordination logic: pure planning helpers plus a Qt-aware orchestrator.

The free functions stay pure and independently testable. ``ExportCoordinator``
is the stateful, Qt-aware orchestrator extracted from ``MainWindow``; it reads
state and widgets through a ``host`` handle (the ``MainWindow``) and calls the
free functions internally.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol

from xfinaudio.application.dj_readiness import write_application_dj_readiness_report
from xfinaudio.application.playlist_file_export import export_playlist_file, preview_playlist_file_export
from xfinaudio.application.serato_playlist_export import export_serato_playlist
from xfinaudio.desktop.export_dependencies import ExportDependencies
from xfinaudio.desktop.serato_metadata_worklist_export import SeratoMetadataWorklistExportMixin
from xfinaudio.desktop.serato_recommendation_export import (
    SeratoRecommendationExportMixin,
    build_serato_export_entry,
    record_export,
)
from xfinaudio.desktop.serato_recommendation_export import (
    plan_serato_export as _plan_serato_export,
)
from xfinaudio.desktop.serato_recommendation_export import (
    write_readiness_sidecars as _write_readiness_sidecars,
)
from xfinaudio.desktop.software_export_coordinator import SoftwareExportCoordinatorMixin
from xfinaudio.exporting.export_readiness import (
    ExportGateDecision,
    ExportGateOperation,
    ExportGateRequest,
    evaluate_export_gate,
)
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    discover_serato_libraries,
)
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

__all__ = [
    "ExportCoordinator",
    "SeratoLibrary",
    "build_serato_export_entry",
    "discover_serato_libraries",
    "evaluate_export_gate",
    "export_playlist_file",
    "export_serato_playlist",
    "plan_serato_export",
    "preview_playlist_file_export",
    "record_export",
    "write_application_dj_readiness_report",
    "write_readiness_sidecars",
]

LOGGER = logging.getLogger(__name__)

_SERATO_EXPORT_HISTORY_LIMIT = 5


def plan_serato_export(*args: Any, **kwargs: Any) -> Any:
    """Compatibility entrypoint with call-time dependency resolution."""
    kwargs.setdefault("discover_libraries", discover_serato_libraries)
    return _plan_serato_export(*args, **kwargs)


def write_readiness_sidecars(*args: Any, **kwargs: Any) -> Any:
    """Compatibility entrypoint with call-time report-writer resolution."""
    kwargs.setdefault("write_report", write_application_dj_readiness_report)
    return _write_readiness_sidecars(*args, **kwargs)


class ExportHost(Protocol):
    """Structural host boundary for ``ExportCoordinator``.

    Declares only the ``MainWindow`` members the coordinator reads or calls,
    decoupling export orchestration from the concrete window type.
    """

    last_recommendation: PlaylistRecommendation | None
    playlist_removed_paths: frozenset[str]
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


class ExportCoordinator(
    SoftwareExportCoordinatorMixin, SeratoRecommendationExportMixin, SeratoMetadataWorklistExportMixin
):
    """Qt-aware export orchestration extracted from MainWindow (first slice).

    State and widget access flow through ``host`` (the ``MainWindow``); pure
    planning is delegated to the module-level free functions.
    """

    def __init__(
        self,
        host: ExportHost,
        on_export_success: Callable[[], None] | None = None,
        dependencies: ExportDependencies | None = None,
    ) -> None:
        self._host = host
        self._on_export_success = on_export_success
        self._injected_dependencies = dependencies

    def _export_dependencies(self) -> ExportDependencies:
        """Resolve injectable dependencies at call time to preserve monkeypatch seams."""
        if self._injected_dependencies is not None:
            return self._injected_dependencies
        return ExportDependencies(
            evaluate_export_gate=evaluate_export_gate,
            preview_playlist_file_export=preview_playlist_file_export,
            export_playlist_file=export_playlist_file,
            export_serato_playlist=export_serato_playlist,
            discover_serato_libraries=discover_serato_libraries,
            write_application_dj_readiness_report=write_application_dj_readiness_report,
            write_readiness_sidecars=write_readiness_sidecars,
        )

    def _build_export_gate_request(self, operation: ExportGateOperation, software: str) -> ExportGateRequest:
        """Build a pure export gate request from current host state."""
        host = self._host
        readiness_status = host.last_dj_readiness_report.status if host.last_dj_readiness_report is not None else None
        return ExportGateRequest(
            operation=operation,
            software=software,
            has_recommendation=host.last_recommendation is not None,
            readiness_status=readiness_status,
            safe_folder=host.settings.export.safe_export_folder,
        )

    def _handle_denied_export_gate(
        self,
        decision: ExportGateDecision,
        operation: ExportGateOperation,
        software: str,
    ) -> bool:
        """Render existing status copy for denied export gate decisions."""
        if decision.allowed:
            return False

        host = self._host
        if decision.code == "missing_recommendation":
            if operation == "preview":
                message = (
                    host.tr("Generate a recommendation before previewing Serato export")
                    if software == "Serato"
                    else host.tr("Generate a recommendation before previewing {0} export").format(software)
                )
            else:
                message = (
                    host.tr("Generate a recommendation before exporting to Serato")
                    if software == "Serato"
                    else host.tr("Generate a recommendation before exporting to {0}").format(software)
                )
        elif decision.code == "blocked_readiness":
            message = host.tr("Resolve blocked readiness checks before exporting.")
        elif decision.code == "missing_safe_folder":
            message = (
                host.tr("Choose a safe export folder before previewing {0} export").format(software)
                if operation == "preview"
                else host.tr("Choose a safe export folder before exporting to {0}").format(software)
            )
        else:
            return False

        host.status_label.setText(message)
        return True

    def selected_software(self) -> str:
        """Return the currently selected DJ software from the Export screen."""
        return self._host._export_screen.software_selector.currentText()
