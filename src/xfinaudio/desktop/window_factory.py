"""Main window runtime factory."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.config.settings import AppSettings
from xfinaudio.desktop.app_state import AppState, SettingsPersistence
from xfinaudio.desktop.audio_player import AudioPlayer
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.dj_readiness_controller import DjReadinessController
from xfinaudio.desktop.export_actions import ExportActions
from xfinaudio.desktop.export_coordinator import ExportCoordinator
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.metadata_view_model import MetadataViewModel
from xfinaudio.desktop.navigation import Navigation
from xfinaudio.desktop.playlist_coordinator import PlaylistCoordinator
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
from xfinaudio.desktop.undo_manager import UndoManager
from xfinaudio.library.playlist_repository import PlaylistRepository


def initialize_window_state(
    window,
    scan_service,
    repository,
    settings: AppSettings | None,
    settings_repository: SettingsPersistence | None,
) -> None:
    """Build the runtime services, view models, and controllers for the main window."""
    workflow_service = PlaylistWorkflowService(scan_service=scan_service, repository=repository)
    window.settings = settings or AppSettings()
    window.settings_repository = settings_repository
    window._state = AppState(
        workflow_service=workflow_service,
        selected_folder=window.settings.library.last_scan_folder,
        settings=window.settings,
    )
    window._is_recommending = False
    window._scan_service = DesktopScanService(workflow_service, parent=window)
    window._recommendation_service = RecommendationService(workflow_service, parent=window)
    window._table_sort_orders = {}
    window._active_song_search_query = ""
    window._library_selected_paths = []
    window._pre_scan_records_by_path = {}
    window._nav = Navigation()
    window._undo_manager = UndoManager()
    window._audio_player = AudioPlayer(parent=window)
    window._audio_player.set_volume(window.settings.audio.preview_volume)
    playlist_db_path = getattr(repository, "db_path", None)
    if playlist_db_path is None:
        playlist_db_path = Path(".") / "xfinaudio_playlists.db"
    window._playlist_repository = PlaylistRepository(playlist_db_path.parent / "playlists.db")
    window._library_vm = LibraryViewModel()
    window._build_vm = BuildViewModel()
    window._review_vm = ReviewViewModel()
    window._export_vm = ExportViewModel()
    window._metadata_vm = MetadataViewModel()
    window._library_screen = LibraryScreen()
    window._build_screen = BuildScreen()
    window._build_screen.spectral_cohesion_slider.setValue(int(round(window.settings.scoring.spectral_cohesion * 100)))
    window._review_screen = ReviewScreen()
    window._export_screen = ExportScreen()
    window._playlists_screen = MyPlaylistsScreen()
    window._playlist_editor = PlaylistEditor()
    window._metadata_screen = MetadataScreen()
    window._live_assistant_screen = LiveAssistantScreen()
    window._search_debounce = QTimer(window)
    window._search_debounce.setSingleShot(True)
    window._search_debounce.setInterval(150)
    window._current_tab_index = 0
    window._playlist_coordinator = PlaylistCoordinator(host=window)
    window._export_coordinator = ExportCoordinator(
        host=window,
        on_export_success=window._playlist_coordinator.save_recommendation,
    )
    window._export_actions = ExportActions(window._export_coordinator)
    window._settings_dialog = None
    window._settings_controller = SettingsController(
        settings_getter=lambda: window.settings,
        settings_setter=lambda value: setattr(window, "settings", value),
        settings_repository=window.settings_repository,
        export_screen=window._export_screen,
        sync_state=window._sync_state,
        tr=window.tr,
        message_parent=window,
        dialog_setter=lambda dialog: setattr(window, "_settings_dialog", dialog),
    )
    window._dj_readiness_controller = DjReadinessController(
        state=window._state,
        review_screen=window._review_screen,
        sync_state=window._sync_state,
        last_report_setter=lambda value: setattr(window, "last_dj_readiness_report", value),
    )
