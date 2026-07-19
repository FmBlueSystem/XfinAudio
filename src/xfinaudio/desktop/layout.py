"""Responsive layout helpers for the desktop shell."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QCoreApplication

from xfinaudio.desktop.main_window_layout import (  # noqa: F401
    build_main_widgets,
    build_main_window_layout,
    responsive_sidebar_width,
)
from xfinaudio.desktop.window_service_wiring import (  # noqa: F401
    apply_main_song_filter,
    selected_main_track_controls,
    set_main_recommendation_sections_expanded,
    set_main_status_bar_visible,
    wire_main_recommendation_service,
    wire_main_scan_service,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls

_SIDEBAR_WIDTH_WIDE = 180
_SIDEBAR_WIDTH_NARROW = 120
_NARROW_BREAKPOINT = 900
_TRACK_TITLE_COLUMN = 0
_TRACK_STATUS_COLUMN = 9
_TRACK_PATH_COLUMN = 11
_RECOMMENDATION_READY_GUIDANCE = QCoreApplication.translate(
    "MainWindow",
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.",
)


def choose_safe_export_folder(self: Any) -> None:
    self._export_actions.choose_safe_export_folder()


def open_main_settings_dialog(self: Any) -> None:
    self._settings_controller.open_settings_dialog()


def on_main_spectral_cohesion_changed(self: Any, value: int) -> None:
    self._settings_controller.on_spectral_cohesion_changed(value)


def set_safe_export_folder(self: Any, folder: Any) -> None:
    self._export_actions.set_safe_export_folder(folder)


def export_dj_readiness_report(self: Any, *, generated_at: Any | None = None) -> None:
    self._export_actions.export_dj_readiness_report(generated_at=generated_at)


def preview_export(
    self: Any,
    *,
    serato_folder: Any | None = None,
    crate_name: str | None = None,
    generated_at: Any | None = None,
) -> None:
    self._export_actions.preview_export(
        serato_folder=serato_folder,
        crate_name=crate_name,
        generated_at=generated_at,
    )


def export_recommendation(
    self: Any,
    *,
    serato_folder: Any | None = None,
    crate_name: str | None = None,
    generated_at: Any | None = None,
) -> None:
    self._export_actions.export_recommendation(
        serato_folder=serato_folder,
        crate_name=crate_name,
        generated_at=generated_at,
    )


def preview_serato_export(
    self: Any,
    *,
    serato_folder: Any | None = None,
    crate_name: str | None = None,
    generated_at: Any | None = None,
) -> None:
    self._export_actions.preview_serato_export(
        serato_folder=serato_folder,
        crate_name=crate_name,
        generated_at=generated_at,
    )


def export_recommendation_to_serato(
    self: Any,
    *,
    serato_folder: Any | None = None,
    crate_name: str | None = None,
    generated_at: Any | None = None,
) -> None:
    self._export_actions.export_recommendation_to_serato(
        serato_folder=serato_folder,
        crate_name=crate_name,
        generated_at=generated_at,
    )


def export_metadata_status_to_serato(
    self: Any,
    *,
    status: str | None = None,
    missing_field: str | None = None,
    serato_folder: Any | None = None,
) -> None:
    self._export_actions.export_metadata_status_to_serato(
        status=status,
        missing_field=missing_field,
        serato_folder=serato_folder,
    )


def scan_selected_folder(self: Any) -> None:
    self._scan_service.scan_selected_folder()


def begin_main_scan_state(self: Any) -> None:
    self._scan_service.begin_scan_state()


def on_main_library_selection_changed(self: Any, paths: list[str]) -> None:
    self._library_controller.on_library_selection_changed(paths)


def cancel_scan(self: Any) -> None:
    self._scan_service.cancel()


def show_tracks(
    self: Any,
    records: list[TrackRecord],
    complete_count: int | None = None,
    incomplete_count: int | None = None,
) -> None:
    """Render scanned records in the desktop table."""
    self._library_controller.show_tracks(records, complete_count, incomplete_count)


def generate_prep_copilot(self: Any) -> None:
    self._prep_copilot.generate()


def apply_prep_copilot_item(self: Any, item: Any) -> None:
    self._prep_copilot.apply_item(item)


def apply_selected_prep_copilot_variant(self: Any) -> None:
    self._prep_copilot.apply_selected_variant()


def recommend_playlist(self: Any) -> None:
    self._recommendation_service.recommend()


def begin_main_recommendation_state(self: Any, candidate_count: int) -> None:
    self._recommendation_service._begin_recommendation_state(candidate_count)


def end_main_recommendation_state(self: Any) -> None:
    self._recommendation_service._end_recommendation_state()


def start_main_recommendation_worker(
    self: Any, records: list[TrackRecord], strategy_name: str, controls: DJControls | None = None
) -> None:
    self._recommendation_service.start_recommendation(records, strategy_name, controls)


def finish_main_recommendation(self: Any, result: Any) -> None:
    self._recommendation_service.on_completed(result)


def fail_main_recommendation(self: Any, error: object) -> None:
    self._recommendation_service.on_failed(error)


def populate_main_dj_readiness_table(self: Any, report: Any) -> None:
    self._dj_readiness_controller.populate_table(report)


def on_main_recommend_requested(self: Any, strategy_name: str, paths: list[str]) -> None:
    self._recommendation_service.on_recommend_requested(strategy_name, paths)


def on_main_copilot_variant_applied(self: Any, index: int) -> None:
    self._prep_copilot.on_variant_applied(index)


def format_main_safe_export_folder_label(self: Any) -> str:
    if not hasattr(self, "_settings_controller"):
        folder = self.settings.export.safe_export_folder
        if folder is None:
            return self.tr("No safe export folder selected")
        return self.tr("Safe export folder: {0}").format(folder)
    return self._settings_controller.format_safe_export_folder_label()


def choose_folder(self: Any) -> None:
    self._library_controller.choose_folder()


def set_selected_folder(self: Any, folder: Any) -> None:
    self._library_controller.set_selected_folder(folder)


def persist_main_last_scan_folder(self: Any, folder: Any) -> None:
    self.settings = self.settings.model_copy(
        update={"library": self.settings.library.model_copy(update={"last_scan_folder": folder})}
    )
    if self.settings_repository is not None:
        self.settings_repository.save(self.settings)


def populate_main_track_table(self: Any, records: list[TrackRecord]) -> None:
    self._library_controller.populate_track_table(records)


def apply_main_window_song_filter(self: Any, query: str | None = None, *, clear_selection: bool = False) -> None:
    self._library_controller.apply_song_filter(query, clear_selection=clear_selection)


def selected_main_metadata_status_filter(self: Any) -> str | None:
    return self._library_controller.selected_metadata_status_filter()


def selected_main_missing_metadata_filter(self: Any) -> str | None:
    return self._library_controller.selected_missing_metadata_filter()


def metadata_main_status_records(self: Any, status: str) -> list[TrackRecord]:
    return self._library_controller.metadata_status_records(status)


def metadata_main_missing_field_records(self: Any, missing_field: str) -> list[TrackRecord]:
    return self._library_controller.metadata_missing_field_records(missing_field)


def restore_main_tracks(self: Any, records: list[TrackRecord]) -> None:
    self._library_controller.restore_persisted_tracks(records)


def start_main_spectral_completion_worker(self: Any, records: list[TrackRecord]) -> None:
    self._library_controller.start_spectral_completion_worker(records)


def cancel_main_spectral_completion_worker(self: Any) -> None:
    self._library_controller.cancel_spectral_completion_worker()


def on_main_spectral_progress_updated(self: Any, processed_count: int, total_count: int) -> None:
    self._library_controller.on_spectral_progress_updated(processed_count, total_count)


def on_main_spectral_profile_ready(self: Any, path: str, profile: object) -> None:
    self._library_controller.on_spectral_profile_ready(path, profile)


def on_main_spectral_completion_finished(self: Any) -> None:
    self._library_controller.on_spectral_completion_finished()


def clear_main_scan_dependent_state_via_controller(self: Any) -> None:
    self._library_controller.clear_scan_dependent_state()


def refresh_main_idle_action_state(self: Any) -> None:
    self._library_controller.refresh_idle_action_state()
