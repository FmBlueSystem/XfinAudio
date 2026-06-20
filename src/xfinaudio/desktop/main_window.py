"""PySide6 desktop walking skeleton for XfinAudio."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QMainWindow

from xfinaudio.application.playlist_workflow import ScanService
from xfinaudio.config.settings import AppSettings, WindowSettings
from xfinaudio.desktop import layout as _layout
from xfinaudio.desktop import rendering as _rendering
from xfinaudio.desktop import shell_layout_compat as _shell_layout_compat
from xfinaudio.desktop import shell_state_compat as _shell_state_compat
from xfinaudio.desktop.app_state import AppState, SettingsPersistence
from xfinaudio.desktop.menu import Menu
from xfinaudio.desktop.prep_copilot import PrepCopilotController
from xfinaudio.desktop.recommendation_render import clear_recommendation_review as render_clear_recommendation_review
from xfinaudio.desktop.recommendation_render import render_recommendation
from xfinaudio.desktop.recommendation_render import show_transition_review as render_transition_review
from xfinaudio.desktop.shortcuts import bind_main_window_shortcuts
from xfinaudio.desktop.table_sorting import connect_table_sorting
from xfinaudio.desktop.visual_design import apply_visual_design
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.ports import TrackRepositoryPort
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.candidate_pool import build_recommendation_pool
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

LOGGER = logging.getLogger(__name__)

_NARROW_BREAKPOINT = _layout._NARROW_BREAKPOINT
_SIDEBAR_WIDTH_NARROW = _layout._SIDEBAR_WIDTH_NARROW
_SIDEBAR_WIDTH_WIDE = _layout._SIDEBAR_WIDTH_WIDE
responsive_sidebar_width = _layout.responsive_sidebar_width
format_quality_summary = _rendering.format_quality_summary
format_recommendation_warning = _rendering.format_recommendation_warning
_TEST_COMPAT_EXPORTS = (Qt, subprocess)

_EMPTY_REVIEW_SUMMARY = QCoreApplication.translate("MainWindow", "No recommendation is ready for review.")
_RECOMMENDATION_READY_GUIDANCE = QCoreApplication.translate(
    "MainWindow",
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.",
)
_DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT = 25
_SCREEN_NAMES = ["library", "build", "review", "export", "playlists", "metadata", "live"]

_APP_STATE_ATTRIBUTES = _shell_state_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES


class MainWindow(QMainWindow):
    def __getattr__(self, name: str) -> Any:
        value = _shell_state_compat.try_get_legacy_app_state_attribute(self, name)
        if not _shell_state_compat.is_missing_legacy_attribute(value):
            return value
        raise AttributeError(name)

    def __setattr__(self, name: str, value: object) -> None:
        if _shell_state_compat.try_set_legacy_app_state_attribute(self, name, value):
            return
        super().__setattr__(name, value)

    def __init__(
        self,
        *,
        scan_service: ScanService,
        repository: TrackRepositoryPort,
        settings: AppSettings | None = None,
        settings_repository: SettingsPersistence | None = None,
    ) -> None:
        super().__init__()
        self._initialize_window_state(scan_service, repository, settings, settings_repository)

        self._build_widgets()
        self._initialize_library_controller()
        self._prep_copilot = PrepCopilotController(
            build_screen=self._build_screen,
            build_vm=self._build_vm,
            state=self,
            workflow_service=self.workflow_service,
            on_state_changed=self._sync_state,
            on_status_message=self.status_label.setText,
        )
        self._wire_scan_service()
        self._wire_recommendation_service()

        self._connect_screens()
        apply_visual_design(self)
        self._build_layout()
        self._initialize_app_controller()
        self._menu = Menu(self)  # type: ignore[reportArgumentType]
        self._menu.build(self.menuBar())
        self._restore_window_geometry()
        self._sync_state()

    def closeEvent(self, event: object) -> None:
        self._audio_player.stop()
        self._scan_service.cancel()
        if hasattr(self, "_library_controller"):
            self._cancel_spectral_completion_worker()
        self._recommendation_service.cancel()
        self._persist_window_geometry()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _build_layout(self) -> None:
        _layout.build_main_window_layout(self)

    def _on_sidebar_row_changed(self, index: int) -> None:
        previous_index = self.workflow_tabs.currentIndex()
        if not self.workflow_tabs.isTabEnabled(index):
            self.workflow_sidebar.setCurrentRow(previous_index)
            return
        self.workflow_tabs.setCurrentIndex(index)
        if self.workflow_tabs.currentIndex() != index:
            self.workflow_sidebar.setCurrentRow(previous_index)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._responsive_layout.apply(self.width())

    def _apply_responsive_layout(self, window_width: int) -> None:
        self._responsive_layout.apply(window_width)

    def set_full_screen(self, enabled: bool) -> None:
        self._responsive_layout.set_full_screen(enabled)

    def _restore_window_geometry(self) -> None:
        window = self.settings.window
        if window.width is not None and window.height is not None:
            self.resize(window.width, window.height)
        if window.x is not None and window.y is not None:
            self.move(window.x, window.y)

    def _persist_window_geometry(self) -> None:
        if self.settings_repository is None:
            return
        geometry = self.geometry()
        self.settings = self.settings.model_copy(
            update={
                "window": WindowSettings(
                    width=geometry.width(),
                    height=geometry.height(),
                    x=geometry.x(),
                    y=geometry.y(),
                ),
            }
        )
        self.settings_repository.save(self.settings)

    def _initialize_window_state(
        self,
        scan_service: ScanService,
        repository: TrackRepositoryPort,
        settings: AppSettings | None,
        settings_repository: SettingsPersistence | None,
    ) -> None:
        from xfinaudio.desktop.window_factory import initialize_window_state

        initialize_window_state(self, scan_service, repository, settings, settings_repository)

    def _wire_scan_service(self) -> None:
        _layout.wire_main_scan_service(self)

    def _initialize_library_controller(self) -> None:
        from xfinaudio.desktop.window_factory import initialize_library_controller

        initialize_library_controller(self, LOGGER)

    def _replace_app_state(self, state: AppState) -> None:
        from xfinaudio.desktop.window_factory import replace_app_state

        replace_app_state(self, state)

    def _initialize_app_controller(self) -> None:
        from xfinaudio.desktop.window_factory import initialize_app_controller

        initialize_app_controller(self, _SCREEN_NAMES)

    def _wire_recommendation_service(self) -> None:
        _layout.wire_main_recommendation_service(self)

    def _render_tab(self, index: int, lightweight: bool = False) -> None:
        self._app_controller.render_tab(index, lightweight)

    def _refresh_state_fields(self) -> None:
        self._app_controller.refresh_state_fields()

    def _sync_state(self) -> None:
        self._app_controller.sync_state()

    def _render_screens(self) -> None:
        self._app_controller.render_screens()

    def _on_tab_changed(self, index: int) -> None:
        self._app_controller.on_tab_changed(index)

    def _update_tab_states(self) -> None:
        self._app_controller.update_tab_states()

    def _build_widgets(self) -> None:
        _layout.build_main_widgets(self)

    def choose_folder(self) -> None:
        self._library_controller.choose_folder()

    def _refresh_idle_action_state(self) -> None:
        self._library_controller.refresh_idle_action_state()

    def _on_library_selection_changed(self, paths: list[str]) -> None:
        self._library_controller.on_library_selection_changed(paths)

    def show_tracks(
        self, records: list[Any], complete_count: int | None = None, incomplete_count: int | None = None
    ) -> None:
        self._library_controller.show_tracks(records, complete_count, incomplete_count)

    def set_selected_folder(self, folder: Any) -> None:
        self._library_controller.set_selected_folder(folder)

    def _persist_last_scan_folder(self, folder: Any) -> None:
        self._library_controller._persist_last_scan_folder(folder)

    def _populate_track_table(self, records: list[Any]) -> None:
        self._library_controller.populate_track_table(records)

    def _apply_song_filter(self, query: str | None = None, *, clear_selection: bool = False) -> None:
        self._library_controller.apply_song_filter(query, clear_selection=clear_selection)

    def restore_persisted_tracks(self, records: list[Any]) -> None:
        self._library_controller.restore_persisted_tracks(records)

    def _selected_metadata_status_filter(self) -> str | None:
        return self._library_controller.selected_metadata_status_filter()

    def _selected_missing_metadata_filter(self) -> str | None:
        return self._library_controller.selected_missing_metadata_filter()

    def _metadata_status_records(self, status: str) -> list[Any]:
        return self._library_controller.metadata_status_records(status)

    def _metadata_missing_field_records(self, missing_field: str) -> list[Any]:
        return self._library_controller.metadata_missing_field_records(missing_field)

    def generate_prep_copilot(self) -> None:
        self._prep_copilot.generate()

    def _apply_prep_copilot_item(self, item: Any) -> None:
        self._prep_copilot.apply_item(item)

    def apply_selected_prep_copilot_variant(self) -> None:
        self._prep_copilot.apply_selected_variant()

    def recommend_playlist(self) -> None:
        self._recommendation_service.recommend()

    def _begin_recommendation_state(self, candidate_count: int) -> None:
        self._recommendation_service._begin_recommendation_state(candidate_count)

    def _end_recommendation_state(self) -> None:
        self._recommendation_service._end_recommendation_state()

    def _start_recommendation_worker(
        self, records: list[TrackRecord], strategy_name: str, controls: DJControls | None = None
    ) -> None:
        self._recommendation_service.start_recommendation(records, strategy_name, controls)

    def _finish_recommendation(self, result: Any) -> None:
        self._recommendation_service.on_completed(result)

    def _fail_recommendation(self, error: object) -> None:
        self._recommendation_service.on_failed(error)

    def _populate_dj_readiness_table(self, report: DjReadinessReport) -> None:
        self._dj_readiness_controller.populate_table(report)

    def _on_recommend_requested(self, strategy_name: str, paths: list[str]) -> None:
        self._recommendation_service.on_recommend_requested(strategy_name, paths)

    def choose_safe_export_folder(self) -> None:
        self._export_actions.choose_safe_export_folder()

    def set_safe_export_folder(self, folder: Any) -> None:
        self._export_actions.set_safe_export_folder(folder)

    def _format_safe_export_folder_label(self) -> str:
        if not hasattr(self, "_settings_controller"):
            folder = self.settings.export.safe_export_folder
            if folder is None:
                return self.tr("No safe export folder selected")
            return self.tr("Safe export folder: {0}").format(folder)
        return self._settings_controller.format_safe_export_folder_label()

    def export_dj_readiness_report(self, *, generated_at: Any | None = None) -> None:
        self._export_actions.export_dj_readiness_report(generated_at=generated_at)

    def preview_export(
        self,
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
        self,
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
        self,
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
        self,
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
        self,
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

    def _open_settings_dialog(self) -> None:
        self._settings_controller.open_settings_dialog()

    def _on_spectral_cohesion_changed(self, value: int) -> None:
        self._settings_controller.on_spectral_cohesion_changed(value)

    def scan_selected_folder(self) -> None:
        self._scan_service.scan_selected_folder()

    def _begin_scan_state(self) -> None:
        self._scan_service.begin_scan_state()

    def cancel_scan(self) -> None:
        self._scan_service.cancel()

    def _clear_scan_dependent_state(self) -> None:
        self._library_controller.clear_scan_dependent_state()

    def _connect_screens(self) -> None:
        self._keyboard_shortcuts = bind_main_window_shortcuts(self)
        self._search_debounce.timeout.connect(lambda: self._apply_song_filter(clear_selection=True))
        self._scan_service.scan_progress_updated.connect(self._scan_service.on_progress)
        self._scan_service.scan_completed.connect(self._scan_service.on_completed)
        self._scan_service.scan_failed.connect(self._scan_service.on_failed)
        self._recommendation_service.recommendation_completed.connect(self._recommendation_service.on_completed)
        self._recommendation_service.recommendation_failed.connect(self._recommendation_service.on_failed)
        self.status_bar_toggle.toggled.connect(lambda visible: _layout.set_main_status_bar_visible(self, visible))
        self._audio_player.state_changed.connect(self._library_controller.on_player_state_changed)
        self._audio_player.error_occurred.connect(self._library_controller.on_player_error)
        for screen in (
            self._library_screen,
            self._build_screen,
            self._review_screen,
            self._export_screen,
            self._metadata_screen,
            self._playlists_screen,
            self._playlist_editor,
            self._live_assistant_screen,
        ):
            screen.connect_signals(self)
        self._playlist_coordinator.connect_signals()
        self._playlist_coordinator.refresh_list()
        for table in (
            self._library_screen.tracks_table,
            self._review_screen.transition_table,
            self._review_screen.readiness_table,
            self._export_screen.history_table,
        ):
            callback = (
                (lambda: self._apply_song_filter(clear_selection=False))
                if table is self._library_screen.tracks_table
                else None
            )
            connect_table_sorting(table, self._table_sort_orders, callback)

    @classmethod
    def with_defaults(cls, db_path: Path, settings_path: Path | None = None) -> MainWindow:
        from xfinaudio.desktop.window_factory import with_defaults

        return with_defaults(cls, db_path, settings_path)

    def _apply_settings(self, new_settings: AppSettings) -> None:
        if not hasattr(self, "_settings_controller"):
            from xfinaudio.desktop.settings_controller import SettingsController

            SettingsController(
                settings_getter=lambda: self.settings,
                settings_setter=lambda value: setattr(self, "settings", value),
                settings_repository=self.settings_repository,
                export_screen=self._export_screen,
                sync_state=self._sync_state,
                tr=self.tr,
                message_parent=self,
                dialog_setter=lambda dialog: setattr(self, "_settings_dialog", dialog),
            ).apply_settings(new_settings)
            return
        self._settings_controller.apply_settings(new_settings)

    def _selected_track_controls(self) -> DJControls | None:
        return _layout.selected_main_track_controls(self)

    def _desktop_recommendation_records(self, controls: DJControls | None) -> list[TrackRecord]:
        return build_recommendation_pool(self.scanned_records, controls, _DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT)

    def show_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        explanation: PlaylistExplanation | None = None,
    ) -> None:
        render_recommendation(
            records=records,
            review_screen=self._review_screen,
            library_vm=self._library_vm,
            build_vm=self._build_vm,
            review_vm=self._review_vm,
            state=self._state,
            tr=self.tr,
            set_sections_expanded=lambda expanded: _layout.set_main_recommendation_sections_expanded(self, expanded),
            sync_state=self._sync_state,
            render_tab=self._render_tab,
        )

    def clear_recommendation_review(self) -> None:
        render_clear_recommendation_review(
            review_screen=self._review_screen,
            build_screen=self._build_screen,
            empty_summary=_EMPTY_REVIEW_SUMMARY,
            tr=self.tr,
            set_sections_expanded=lambda expanded: _layout.set_main_recommendation_sections_expanded(self, expanded),
        )

    def _show_dj_readiness(
        self,
        recommendation: PlaylistRecommendation,
        quality_report: RecommendationQualityReport,
        *,
        serato_plan: Any | None = None,
        serato_volume_root: Path | None = None,
    ) -> None:
        """Render operational DJ readiness for the current recommendation."""
        self._dj_readiness_controller.show(
            recommendation,
            quality_report,
            serato_plan=serato_plan,
            serato_volume_root=serato_volume_root,
        )

    def show_transition_review(self, explanation: PlaylistExplanation) -> None:
        render_transition_review(review_screen=self._review_screen, explanation=explanation, tr=self.tr)


_shell_layout_compat.install_legacy_layout_methods(MainWindow)
