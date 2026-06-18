"""PySide6 desktop walking skeleton for XfinAudio."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService, ScanService, TrackPersistence
from xfinaudio.config.settings import AppSettings, WindowSettings
from xfinaudio.desktop import layout as _layout
from xfinaudio.desktop import rendering as _rendering
from xfinaudio.desktop.app_controller import (
    AppController,
    AppControllerScreens,
    AppControllerStateAccess,
    AppControllerViewModels,
)
from xfinaudio.desktop.app_state import AppState, SettingsPersistence
from xfinaudio.desktop.audio_player import AudioPlayer
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.dj_readiness_controller import DjReadinessController
from xfinaudio.desktop.export_actions import ExportActions
from xfinaudio.desktop.export_coordinator import ExportCoordinator
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.library_controller import LibraryController, LibraryControllerAccess, LibraryControllerWidgets
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.menu import Menu
from xfinaudio.desktop.metadata_view_model import MetadataViewModel
from xfinaudio.desktop.navigation import Navigation
from xfinaudio.desktop.playlist_coordinator import PlaylistCoordinator
from xfinaudio.desktop.prep_copilot import PrepCopilotController
from xfinaudio.desktop.recommendation_presenter import build_recommendation_pool
from xfinaudio.desktop.recommendation_render import clear_recommendation_review as render_clear_recommendation_review
from xfinaudio.desktop.recommendation_render import render_recommendation
from xfinaudio.desktop.recommendation_render import show_transition_review as render_transition_review
from xfinaudio.desktop.recommendation_service import RecommendationService
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.scan_service import ScanService as DesktopScanService
from xfinaudio.desktop.screens import (
    BuildScreen,
    ExportScreen,
    LibraryScreen,
    LiveAssistantScreen,
    MetadataScreen,
    MyPlaylistsScreen,
    PlaylistEditor,
    ReviewScreen,
)
from xfinaudio.desktop.settings_controller import SettingsController
from xfinaudio.desktop.shortcuts import bind_main_window_shortcuts
from xfinaudio.desktop.table_sorting import connect_table_sorting, sort_table_by_column
from xfinaudio.desktop.theme import (
    _COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT,
    _COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT,
)
from xfinaudio.desktop.undo_manager import Command, UndoManager
from xfinaudio.desktop.undo_toolbar import UndoToolbar
from xfinaudio.desktop.visual_design import apply_compact_mac_layout, apply_compact_table_columns, apply_visual_design
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.scan_service import MetadataScanService, ScanCancellationToken
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import PrepCopilotPlan

LOGGER = logging.getLogger(__name__)

_NARROW_BREAKPOINT = _layout._NARROW_BREAKPOINT
_SIDEBAR_WIDTH_NARROW = _layout._SIDEBAR_WIDTH_NARROW
_SIDEBAR_WIDTH_WIDE = _layout._SIDEBAR_WIDTH_WIDE
responsive_sidebar_width = _layout.responsive_sidebar_width
format_quality_summary = _rendering.format_quality_summary
format_recommendation_warning = _rendering.format_recommendation_warning

_EMPTY_REVIEW_SUMMARY = QCoreApplication.translate("MainWindow", "No recommendation is ready for review.")
_RECOMMENDATION_READY_GUIDANCE = QCoreApplication.translate(
    "MainWindow",
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.",
)
_DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT = 25
_SCREEN_NAMES = ["library", "build", "review", "export", "playlists", "metadata", "live"]

_TRACK_TITLE_COLUMN = 0
_TRACK_COLOR_COLUMN = 6
_TRACK_MISSING_COLUMN = 7
_TRACK_STATUS_COLUMN = 9
_TRACK_PATH_COLUMN = 11

_MISSING_METADATA_FILTERS = {
    QCoreApplication.translate("MainWindow", "Missing BPM"): "bpm",
    QCoreApplication.translate("MainWindow", "Missing Key"): "camelot_key",
    QCoreApplication.translate("MainWindow", "Missing Energy"): "energy_level",
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        scan_service: ScanService,
        repository: TrackPersistence,
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

        self._connect_widget_signals()
        self._apply_visual_design()
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
        _layout.build_main_layout(self)

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
        repository: TrackPersistence,
        settings: AppSettings | None,
        settings_repository: SettingsPersistence | None,
    ) -> None:
        """Initialize constructor dependencies and runtime state before widgets are created."""
        self.workflow_service = PlaylistWorkflowService(scan_service=scan_service, repository=repository)
        self.settings = settings or AppSettings()
        self.settings_repository = settings_repository
        self._state = AppState(
            selected_folder=self.settings.library.last_scan_folder,
            settings=self.settings,
        )
        self._is_recommending: bool = False
        self._scan_service = DesktopScanService(self.workflow_service, parent=self)
        self._recommendation_service = RecommendationService(self.workflow_service, parent=self)
        self._table_sort_orders: dict[int, Qt.SortOrder] = {}
        self._active_song_search_query = ""
        self._library_selected_paths: list[str] = []
        self._pre_scan_records_by_path: dict[str, TrackRecord] = {}
        self._nav = Navigation()
        self._undo_manager = UndoManager()
        self._audio_player = AudioPlayer(parent=self)
        self._audio_player.set_volume(self.settings.audio.preview_volume)
        playlist_db_path = getattr(repository, "db_path", None)
        if playlist_db_path is None:
            playlist_db_path = Path(".") / "xfinaudio_playlists.db"
        self._playlist_repository = PlaylistRepository(playlist_db_path.parent / "playlists.db")
        self._library_vm = LibraryViewModel()
        self._build_vm = BuildViewModel()
        self._review_vm = ReviewViewModel()
        self._export_vm = ExportViewModel()
        self._metadata_vm = MetadataViewModel()
        self._library_screen = LibraryScreen()
        self._build_screen = BuildScreen()
        self._build_screen.spectral_cohesion_slider.setValue(int(round(self.settings.scoring.spectral_cohesion * 100)))
        self._review_screen = ReviewScreen()
        self._export_screen = ExportScreen()
        self._playlists_screen = MyPlaylistsScreen()
        self._playlist_editor = PlaylistEditor()
        self._metadata_screen = MetadataScreen()
        self._live_assistant_screen = LiveAssistantScreen()
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(150)
        self._current_tab_index: int = 0
        self._playlist_coordinator = PlaylistCoordinator(host=self)  # type: ignore[reportArgumentType]
        self._export_coordinator = ExportCoordinator(
            host=self,  # type: ignore[reportArgumentType]
            on_export_success=self._playlist_coordinator.save_recommendation,
        )
        self._export_actions = ExportActions(self._export_coordinator)
        self._settings_dialog: object | None = None
        self._settings_controller = SettingsController(
            settings_getter=lambda: self.settings,
            settings_setter=lambda value: setattr(self, "settings", value),
            settings_repository=self.settings_repository,
            export_screen=self._export_screen,
            sync_state=self._sync_state,
            tr=self.tr,
            message_parent=self,
            dialog_setter=lambda dialog: setattr(self, "_settings_dialog", dialog),
        )
        self._dj_readiness_controller = DjReadinessController(
            state=self._state,
            review_screen=self._review_screen,
            sync_state=self._sync_state,
            last_report_setter=lambda value: setattr(self, "last_dj_readiness_report", value),
        )

    def _wire_scan_service(self) -> None:
        _layout.wire_main_scan_service(self)

    def _initialize_library_controller(self) -> None:
        self._library_controller = LibraryController(
            state=self._state,
            workflow_service=self.workflow_service,
            widgets=LibraryControllerWidgets(
                library_screen=self._library_screen,
                build_screen=self._build_screen,
                review_screen=self._review_screen,
                export_screen=self._export_screen,
                metadata_screen=self._metadata_screen,
                folder_label=self.folder_label,
                library_guidance_label=self.library_guidance_label,
                recommendation_guidance_label=self.recommendation_guidance_label,
                status_label=self.status_label,
            ),
            access=LibraryControllerAccess(
                settings_getter=lambda: self.settings,
                settings_setter=lambda value: setattr(self, "settings", value),
                settings_repository=self.settings_repository,
                selected_paths=self._library_selected_paths,
                pre_scan_records_by_path=self._pre_scan_records_by_path,
                set_applied_copilot_variant=self._set_applied_copilot_variant,
                set_recommendation_sections_expanded=self._set_recommendation_sections_expanded,
                clear_recommendation_review=self.clear_recommendation_review,
                selected_track_controls=self._selected_track_controls,
                apply_song_filter=lambda *args, **kwargs: self._apply_song_filter(*args, **kwargs),
                state_setter=self._replace_app_state,
            ),
            audio_player=self._audio_player,
            sync_state=self._sync_state,
            tr=self.tr,
            log=LOGGER,
            parent=self,
        )

    def _replace_app_state(self, state: AppState) -> None:
        self._state = state
        if hasattr(self, "_app_controller"):
            self._app_controller._state = state
        if hasattr(self, "_dj_readiness_controller"):
            self._dj_readiness_controller._state = state
        if hasattr(self, "_scan_service"):
            self._scan_service._state = state
        if hasattr(self, "_recommendation_service"):
            self._recommendation_service._state = state
        if hasattr(self, "_prep_copilot"):
            self._prep_copilot._state = self

    def _initialize_app_controller(self) -> None:
        self._app_controller = AppController(
            state=self._state,
            nav=self._nav,
            workflow_tabs=self.workflow_tabs,
            workflow_sidebar=self.workflow_sidebar,
            screen_names=_SCREEN_NAMES,
            screens=AppControllerScreens(
                library=self._library_screen,
                build=self._build_screen,
                review=self._review_screen,
                export=self._export_screen,
                metadata=self._metadata_screen,
                live_assistant=self._live_assistant_screen,
            ),
            view_models=AppControllerViewModels(
                library=self._library_vm,
                build=self._build_vm,
                review=self._review_vm,
                export=self._export_vm,
                metadata=self._metadata_vm,
            ),
            access=AppControllerStateAccess(
                settings=lambda: self.settings,
                is_scanning=lambda: self.current_scan_cancellation_token is not None,
                is_recommending=lambda: self._is_recommending,
                selected_library_paths=lambda: self._library_selected_paths,
                records_by_path=lambda: self._records_by_path,
                scanned_records=lambda: self.scanned_records,
                render_screens=lambda: self._render_screens(),
            ),
        )

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

    @property
    def workflow_service(self) -> PlaylistWorkflowService:
        return self._workflow_service

    @workflow_service.setter
    def workflow_service(self, value: PlaylistWorkflowService) -> None:
        self._workflow_service = value
        if hasattr(self, "_scan_service"):
            self._scan_service.workflow_service = value
        if hasattr(self, "_recommendation_service"):
            self._recommendation_service.workflow_service = value

    @property
    def current_scan_cancellation_token(self) -> ScanCancellationToken | None:
        return self._scan_service.current_scan_cancellation_token

    @current_scan_cancellation_token.setter
    def current_scan_cancellation_token(self, value: ScanCancellationToken | None) -> None:
        self._scan_service.current_scan_cancellation_token = value

    @property
    def selected_folder(self) -> Path | None:
        return self._state.selected_folder

    @selected_folder.setter
    def selected_folder(self, value: Path | None) -> None:
        self._state.selected_folder = value

    @property
    def scanned_records(self) -> list[TrackRecord]:
        return self._state.scanned_records

    @scanned_records.setter
    def scanned_records(self, value: list[TrackRecord]) -> None:
        self._state.scanned_records = value

    @property
    def _records_by_path(self) -> dict[str, TrackRecord]:
        return self._state.records_by_path

    @_records_by_path.setter
    def _records_by_path(self, value: dict[str, TrackRecord]) -> None:
        self._state.records_by_path = value

    @property
    def last_recommendation(self) -> PlaylistRecommendation | None:
        return self._state.last_recommendation

    @last_recommendation.setter
    def last_recommendation(self, value: PlaylistRecommendation | None) -> None:
        self._state.last_recommendation = value

    @property
    def last_playlist_explanation(self) -> PlaylistExplanation | None:
        return self._state.last_playlist_explanation

    @last_playlist_explanation.setter
    def last_playlist_explanation(self, value: PlaylistExplanation | None) -> None:
        self._state.last_playlist_explanation = value

    @property
    def last_quality_report(self) -> RecommendationQualityReport | None:
        return self._state.last_quality_report

    @last_quality_report.setter
    def last_quality_report(self, value: RecommendationQualityReport | None) -> None:
        self._state.last_quality_report = value

    @property
    def last_dj_readiness_report(self) -> DjReadinessReport | None:
        return self._state.last_dj_readiness_report

    @last_dj_readiness_report.setter
    def last_dj_readiness_report(self, value: DjReadinessReport | None) -> None:
        self._state.last_dj_readiness_report = value

    @property
    def last_prep_copilot_plan(self) -> PrepCopilotPlan | None:
        return self._state.last_prep_copilot_plan

    @last_prep_copilot_plan.setter
    def last_prep_copilot_plan(self, value: PrepCopilotPlan | None) -> None:
        self._state.last_prep_copilot_plan = value

    @property
    def applied_prep_copilot_variant_name(self) -> str | None:
        return self._state.applied_variant_name

    @applied_prep_copilot_variant_name.setter
    def applied_prep_copilot_variant_name(self, value: str | None) -> None:
        self._state.applied_variant_name = value

    @property
    def serato_export_history(self) -> list[dict[str, str]]:
        return self._state.serato_export_history

    @serato_export_history.setter
    def serato_export_history(self, value: list[dict[str, str]]) -> None:
        self._state.serato_export_history = value

    @property
    def excluded_paths(self) -> frozenset[str]:
        return self._state.excluded_paths

    @excluded_paths.setter
    def excluded_paths(self, value: frozenset[str]) -> None:
        self._state.excluded_paths = value

    @property
    def locked_paths(self) -> frozenset[str]:
        return self._state.locked_paths

    @locked_paths.setter
    def locked_paths(self, value: frozenset[str]) -> None:
        self._state.locked_paths = value

    @property
    def playlist_removed_paths(self) -> frozenset[str]:
        return self._state.playlist_removed_paths

    @playlist_removed_paths.setter
    def playlist_removed_paths(self, value: frozenset[str]) -> None:
        self._state.playlist_removed_paths = value

    def _update_tab_states(self) -> None:
        self._app_controller.update_tab_states()

    def _build_widgets(self) -> None:
        _layout.build_main_widgets(self)

    def _connect_widget_signals(self) -> None:
        self._connect_keyboard_shortcuts()
        self._build_screen.copilot_table.itemDoubleClicked.connect(self._apply_prep_copilot_item)
        self._library_screen.tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)
        self._library_screen.search_input.textChanged.connect(self._search_debounce.start)
        self._search_debounce.timeout.connect(lambda: self._apply_song_filter(clear_selection=True))
        self._metadata_screen.status_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self._metadata_screen.missing_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self._metadata_screen.export_button.clicked.connect(lambda: self.export_metadata_status_to_serato())
        self._scan_service.scan_progress_updated.connect(self._scan_service.on_progress)
        self._scan_service.scan_completed.connect(self._scan_service.on_completed)
        self._scan_service.scan_failed.connect(self._scan_service.on_failed)
        self._recommendation_service.recommendation_completed.connect(self._recommendation_service.on_completed)
        self._recommendation_service.recommendation_failed.connect(self._recommendation_service.on_failed)
        self._library_screen.folder_change_requested.connect(self.choose_folder)
        self._library_screen.scan_requested.connect(self.scan_selected_folder)
        self._library_screen.cancel_scan_requested.connect(self.cancel_scan)
        self.status_bar_toggle.toggled.connect(self._set_status_bar_visible)
        self._library_screen.selection_changed.connect(self._on_library_selection_changed)
        self._library_screen.metadata_screen_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(5))
        self._library_screen.proceed_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(1))
        self._library_screen.settings_requested.connect(self._open_settings_dialog)
        self._library_screen.filters_cleared.connect(self._on_library_filters_cleared)
        self._build_screen.recommend_requested.connect(self._on_recommend_requested)
        self._build_screen.spectral_cohesion_changed.connect(self._on_spectral_cohesion_changed)
        self._build_screen.copilot_generate_requested.connect(self.generate_prep_copilot)
        self._build_screen.copilot_variant_applied.connect(self._on_copilot_variant_applied)
        self._build_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(0))
        self._build_screen.proceed_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        self._build_screen.exclude_requested.connect(self._on_exclude_requested)
        self._build_screen.lock_requested.connect(self._on_lock_requested)
        self._build_screen.clear_constraints_requested.connect(self._on_clear_constraints)
        self._review_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(1))
        self._review_screen.proceed_to_export_requested.connect(self._on_proceed_to_export)
        self._review_screen.track_remove_requested.connect(self._on_track_remove_requested)
        self._review_screen.track_play_requested.connect(self._on_track_play_requested)
        self._library_screen.track_play_requested.connect(self._on_track_play_requested)
        self._library_screen.play_requested.connect(self._on_preview_play_requested)
        self._library_screen.pause_requested.connect(self._audio_player.pause)
        self._audio_player.state_changed.connect(self._on_player_state_changed)
        self._audio_player.error_occurred.connect(self._on_player_error)
        self._export_screen.preview_requested.connect(self.preview_export)
        self._export_screen.export_requested.connect(self.export_recommendation)
        self._export_screen.readiness_export_requested.connect(lambda: self.export_dj_readiness_report())
        self._export_screen.safe_folder_change_requested.connect(self.choose_safe_export_folder)
        self._export_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        self._metadata_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(0))
        self._metadata_screen.filter_changed.connect(self._sync_state)
        self._metadata_screen.export_requested.connect(self._on_metadata_export_requested)
        self._live_assistant_screen.connect_signals(lambda: self.workflow_tabs, self._on_preview_play_requested)
        self._playlist_coordinator.connect_signals()
        self._playlist_coordinator.refresh_list()
        for table in (
            self._library_screen.tracks_table,
            self._review_screen.transition_table,
            self._review_screen.readiness_table,
            self._export_screen.history_table,
        ):
            self._connect_table_sorting(table)

    def _connect_keyboard_shortcuts(self) -> None:
        self._keyboard_shortcuts = bind_main_window_shortcuts(self)

    def _build_undo_toolbar(self) -> None:
        self._undo_toolbar = UndoToolbar(self._undo_manager, self)
        self.addToolBar(self._undo_toolbar.toolbar)
        self.undo_button = self._undo_toolbar.undo_button
        self.redo_button = self._undo_toolbar.redo_button
        self.undo_history_menu = self._undo_toolbar.undo_history_menu

    def undo(self) -> None:
        self._undo_toolbar.undo()

    def redo(self) -> None:
        self._undo_toolbar.redo()

    def _refresh_undo_state(self) -> None:
        self._undo_toolbar.refresh()

    def _open_selected_library_track(self) -> None:
        selected_rows = sorted({index.row() for index in self._library_screen.tracks_table.selectedIndexes()})
        if not selected_rows:
            return
        path_item = self._library_screen.tracks_table.item(selected_rows[0], _TRACK_PATH_COLUMN)
        if path_item is not None:
            self._on_track_play_requested(path_item.text())

    def _remove_selected_review_track(self) -> None:
        row = self._review_screen.recommendation_table.currentRow()
        path_item = self._review_screen.recommendation_table.item(row, 0)
        if path_item is not None and (path := path_item.data(Qt.ItemDataRole.UserRole)):
            self._on_track_remove_requested(path)

    def _apply_compact_mac_layout(self, layout: QVBoxLayout, status_controls: QHBoxLayout) -> None:
        apply_compact_mac_layout(self, layout, status_controls)

    def _set_status_bar_visible(self, visible: bool) -> None:
        self.status_bar.setVisible(visible)
        self.status_bar_toggle.setChecked(visible)

    def show_status_bar(self) -> None:
        self._set_status_bar_visible(True)

    def _apply_compact_table_columns(self) -> None:
        apply_compact_table_columns(self)

    def _apply_visual_design(self) -> None:
        apply_visual_design(self)

    def _set_recommendation_sections_expanded(self, expanded: bool) -> None:
        maximum_height = 16777215 if expanded else _COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT
        self._review_screen.recommendation_table.setHidden(not expanded)
        self._review_screen.transition_table.setHidden(not expanded)
        self._review_screen.readiness_table.setHidden(not expanded)
        self._review_screen.recommendation_table.setMaximumHeight(maximum_height)
        self._review_screen.transition_table.setMaximumHeight(maximum_height)
        self._review_screen.readiness_table.setMaximumHeight(
            _COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT if expanded else _COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT
        )

    def _connect_table_sorting(self, table: QTableWidget) -> None:
        callback = (
            (lambda: self._apply_song_filter(clear_selection=False))
            if table is self._library_screen.tracks_table
            else None
        )
        connect_table_sorting(table, self._table_sort_orders, callback)

    def _sort_table_by_column(self, table: QTableWidget, column: int) -> None:
        callback = (
            (lambda: self._apply_song_filter(clear_selection=False))
            if table is self._library_screen.tracks_table
            else None
        )
        sort_table_by_column(table, column, self._table_sort_orders, callback)

    @classmethod
    def with_defaults(cls, db_path: Path, settings_path: Path | None = None) -> MainWindow:
        from xfinaudio.config.settings_repository import SettingsRepository
        from xfinaudio.desktop.app import default_settings_path

        settings_repository = SettingsRepository(settings_path or default_settings_path())
        repository = TrackRepository(db_path)
        window = cls(
            scan_service=MetadataScanService(),
            repository=repository,
            settings=settings_repository.load(),
            settings_repository=settings_repository,
        )
        window.restore_persisted_tracks(repository.list_display_tracks())
        return window

    def _format_safe_export_folder_label(self) -> str:
        if not hasattr(self, "_settings_controller"):
            folder = self.settings.export.safe_export_folder
            if folder is None:
                return self.tr("No safe export folder selected")
            return self.tr("Safe export folder: {0}").format(folder)
        return self._settings_controller.format_safe_export_folder_label()

    def choose_folder(self) -> None:
        self._library_controller.choose_folder()

    def set_selected_folder(self, folder: Path) -> None:
        self._library_controller.set_selected_folder(folder)

    def _persist_last_scan_folder(self, folder: Path) -> None:
        self.settings = self.settings.model_copy(
            update={
                "library": self.settings.library.model_copy(update={"last_scan_folder": folder}),
            }
        )
        if self.settings_repository is not None:
            self.settings_repository.save(self.settings)

    def _populate_track_table(self, records: list[TrackRecord]) -> None:
        self._library_controller.populate_track_table(records)

    def _apply_song_filter(self, query: str | None = None, *, clear_selection: bool = False) -> None:
        self._library_controller.apply_song_filter(query, clear_selection=clear_selection)

    def _selected_metadata_status_filter(self) -> str | None:
        return self._library_controller.selected_metadata_status_filter()

    def _selected_missing_metadata_filter(self) -> str | None:
        return self._library_controller.selected_missing_metadata_filter()

    def _metadata_status_records(self, status: str) -> list[TrackRecord]:
        return self._library_controller.metadata_status_records(status)

    def _metadata_missing_field_records(self, missing_field: str) -> list[TrackRecord]:
        return self._library_controller.metadata_missing_field_records(missing_field)

    def restore_persisted_tracks(self, records: list[TrackRecord]) -> None:
        self._library_controller.restore_persisted_tracks(records)

    def _start_spectral_completion_worker(self, records: list[TrackRecord]) -> None:
        self._library_controller.start_spectral_completion_worker(records)

    def _cancel_spectral_completion_worker(self) -> None:
        self._library_controller.cancel_spectral_completion_worker()

    @Slot(int, int)
    def _on_spectral_progress_updated(self, processed_count: int, total_count: int) -> None:
        self._library_controller.on_spectral_progress_updated(processed_count, total_count)

    @Slot(str, object)
    def _on_spectral_profile_ready(self, path: str, profile: object) -> None:
        self._library_controller.on_spectral_profile_ready(path, profile)

    @Slot()
    def _on_spectral_completion_finished(self) -> None:
        self._library_controller.on_spectral_completion_finished()

    def _clear_scan_dependent_state(self) -> None:
        self._library_controller.clear_scan_dependent_state()

    def _refresh_idle_action_state(self) -> None:
        self._library_controller.refresh_idle_action_state()

    def choose_safe_export_folder(self) -> None:
        self._export_actions.choose_safe_export_folder()

    def _open_settings_dialog(self) -> None:
        self._settings_controller.open_settings_dialog()

    def _on_spectral_cohesion_changed(self, value: int) -> None:
        self._settings_controller.on_spectral_cohesion_changed(value)

    def _apply_settings(self, new_settings: AppSettings) -> None:
        if not hasattr(self, "_settings_controller"):
            old_lang = self.settings.ui.language
            self.settings = new_settings
            if self.settings_repository is not None:
                self.settings_repository.save(new_settings)
            self._export_screen.safe_export_folder_label.setText(self._format_safe_export_folder_label())
            self._sync_state()
            if new_settings.ui.language != old_lang:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self,
                    self.tr("Language Changed"),
                    self.tr("Please restart XfinAudio for the language change to take effect."),
                )
            return
        self._settings_controller.apply_settings(new_settings)

    def set_safe_export_folder(self, folder: Path) -> None:
        self._export_actions.set_safe_export_folder(folder)

    def export_dj_readiness_report(self, *, generated_at: datetime | None = None) -> None:
        self._export_actions.export_dj_readiness_report(generated_at=generated_at)

    def preview_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        self._export_actions.preview_export(
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
        self._export_actions.export_recommendation(
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
        self._export_actions.preview_serato_export(
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
        serato_folder: Path | None = None,
    ) -> None:
        self._export_actions.export_metadata_status_to_serato(
            status=status,
            missing_field=missing_field,
            serato_folder=serato_folder,
        )

    def scan_selected_folder(self) -> None:
        self._scan_service.scan_selected_folder()

    def _begin_scan_state(self) -> None:
        self._scan_service.begin_scan_state()

    def _on_library_selection_changed(self, paths: list[str]) -> None:
        self._library_controller.on_library_selection_changed(paths)

    def cancel_scan(self) -> None:
        self._scan_service.cancel()

    def show_tracks(
        self,
        records: list[TrackRecord],
        complete_count: int | None = None,
        incomplete_count: int | None = None,
    ) -> None:
        """Render scanned records in the desktop table."""
        self._library_controller.show_tracks(records, complete_count, incomplete_count)

    def generate_prep_copilot(self) -> None:
        self._prep_copilot.generate()

    def _apply_prep_copilot_item(self, item: QTableWidgetItem) -> None:
        self._prep_copilot.apply_item(item)

    def apply_selected_prep_copilot_variant(self) -> None:
        self._prep_copilot.apply_selected_variant()

    def _set_applied_copilot_variant(self, variant_name: str | None) -> None:
        self.applied_prep_copilot_variant_name = variant_name
        self._sync_state()
        variant_label = self._build_screen.applied_copilot_variant_label
        if variant_name is None:
            variant_label.setText(self.tr("Applied Variant: none"))
            variant_label.setToolTip(self.tr("No Prep Copilot variant is currently applied."))
            return
        variant_label.setText(self.tr("Applied Variant: {0}").format(variant_name))
        variant_label.setToolTip(self.tr("This variant will be used for Serato preview/export."))

    def recommend_playlist(self) -> None:
        self._recommendation_service.recommend()

    def _selected_track_controls(self) -> DJControls | None:
        return _layout.selected_main_track_controls(self)

    def _desktop_recommendation_records(self, controls: DJControls | None) -> list[TrackRecord]:
        return build_recommendation_pool(self.scanned_records, controls, _DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT)

    def _begin_recommendation_state(self, candidate_count: int) -> None:
        self._recommendation_service._begin_recommendation_state(candidate_count)

    def _end_recommendation_state(self) -> None:
        self._recommendation_service._end_recommendation_state()

    def _start_recommendation_worker(
        self, records: list[TrackRecord], strategy_name: str, controls: DJControls | None = None
    ) -> None:
        self._recommendation_service.start_recommendation(records, strategy_name, controls)

    @Slot(object)
    def _finish_recommendation(self, result: Any) -> None:
        self._recommendation_service.on_completed(result)

    @Slot(object)
    def _fail_recommendation(self, error: object) -> None:
        self._recommendation_service.on_failed(error)

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
            set_sections_expanded=self._set_recommendation_sections_expanded,
            sync_state=self._sync_state,
            render_tab=self._render_tab,
        )

    def clear_recommendation_review(self) -> None:
        render_clear_recommendation_review(
            review_screen=self._review_screen,
            build_screen=self._build_screen,
            empty_summary=_EMPTY_REVIEW_SUMMARY,
            tr=self.tr,
            set_sections_expanded=self._set_recommendation_sections_expanded,
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

    def _populate_dj_readiness_table(self, report: DjReadinessReport) -> None:
        self._dj_readiness_controller.populate_table(report)

    def show_transition_review(self, explanation: PlaylistExplanation) -> None:
        render_transition_review(review_screen=self._review_screen, explanation=explanation, tr=self.tr)

    def _on_recommend_requested(self, strategy_name: str, paths: list[str]) -> None:
        self._recommendation_service.on_recommend_requested(strategy_name, paths)

    def _on_copilot_variant_applied(self, index: int) -> None:
        self._prep_copilot.on_variant_applied(index)

    def _on_metadata_export_requested(self, status_filter: str, missing_filter: str) -> None:
        missing_field = _MISSING_METADATA_FILTERS.get(missing_filter)
        norm_status: str | None = (
            status_filter.casefold() if status_filter.casefold() in {"complete", "incomplete"} else None
        )
        self.export_metadata_status_to_serato(status=norm_status, missing_field=missing_field)

    def _on_exclude_requested(self) -> None:
        new_excluded = self._state.excluded_paths | frozenset(self._library_selected_paths)
        self.excluded_paths = new_excluded
        self._sync_state()

    def _on_lock_requested(self) -> None:
        new_locked = self._state.locked_paths | frozenset(self._library_selected_paths)
        self.locked_paths = new_locked
        self._sync_state()

    def _on_clear_constraints(self) -> None:
        self.excluded_paths = frozenset()
        self.locked_paths = frozenset()
        self._sync_state()

    def _on_library_filters_cleared(self, active_labels: list[str]) -> None:
        labels = list(active_labels)
        self._undo_manager.push(
            Command(
                label=self.tr("Clear filters"),
                execute=lambda: self._library_screen.clear_quick_filters(emit_signal=False),
                undo=lambda: self._library_screen.restore_quick_filters(labels),
            )
        )
        self._refresh_undo_state()

    def _on_proceed_to_export(self) -> None:
        vm = ReviewViewModel()
        if vm.can_export(self._state):
            self.workflow_tabs.setCurrentIndex(3)

    def _on_track_remove_requested(self, path: str) -> None:
        if path in self._state.playlist_removed_paths:
            return
        self._apply_track_removed(path)
        self._undo_manager.push(
            Command(
                label=self.tr("Remove {0}").format(Path(path).name),
                execute=lambda: self._apply_track_removed(path),
                undo=lambda: self._apply_track_restored(path),
            )
        )
        self._refresh_undo_state()

    def _apply_track_removed(self, path: str) -> None:
        self._state.playlist_removed_paths = self._state.playlist_removed_paths | {path}
        self._sync_state()

    def _apply_track_restored(self, path: str) -> None:
        self._state.playlist_removed_paths = self._state.playlist_removed_paths - {path}
        self._sync_state()

    def _on_track_play_requested(self, path: str) -> None:
        try:
            subprocess.Popen(["open", path])  # macOS
        except Exception as exc:
            LOGGER.warning("Could not open track %s: %s", path, exc)
            self.status_label.setText(self.tr("Could not open: {0}").format(Path(path).name))

    def _on_preview_play_requested(self, path: str) -> None:
        self._audio_player.stop()
        self._audio_player.load(path)

    def _on_live_load_next(self, path: str) -> None:
        self._live_assistant_screen.load_next(path)

    def _on_player_state_changed(self, state: object) -> None:
        from xfinaudio.desktop.audio_player_state import PlayerState

        if state == PlayerState.PLAYING:
            self._library_screen.set_playing_row(self._audio_player._source_path)
        elif state in (PlayerState.IDLE, PlayerState.ERROR):
            self._library_screen.set_playing_row(None)

    def _on_player_error(self, message: str) -> None:
        LOGGER.warning("Audio preview error: %s", message)
        self._library_screen.set_playing_row(None)
        self.status_label.setText(self.tr("Preview error: {0}").format(message))
