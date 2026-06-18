"""Main window runtime factory."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.config.settings import AppSettings
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
from xfinaudio.library.scan_service import MetadataScanService
from xfinaudio.library.track_repository import TrackRepository


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


def initialize_library_controller(window, log) -> None:
    window._library_controller = LibraryController(
        state=window._state,
        workflow_service=window.workflow_service,
        widgets=LibraryControllerWidgets(
            library_screen=window._library_screen,
            build_screen=window._build_screen,
            review_screen=window._review_screen,
            export_screen=window._export_screen,
            metadata_screen=window._metadata_screen,
            folder_label=window.folder_label,
            library_guidance_label=window.library_guidance_label,
            recommendation_guidance_label=window.recommendation_guidance_label,
            status_label=window.status_label,
        ),
        access=LibraryControllerAccess(
            settings_getter=lambda: window.settings,
            settings_setter=lambda value: setattr(window, "settings", value),
            settings_repository=window.settings_repository,
            selected_paths=window._library_selected_paths,
            pre_scan_records_by_path=window._pre_scan_records_by_path,
            set_applied_copilot_variant=lambda value: window._prep_copilot.set_applied_variant(value),
            set_recommendation_sections_expanded=lambda expanded: __import__(
                "xfinaudio.desktop.layout", fromlist=["set_main_recommendation_sections_expanded"]
            ).set_main_recommendation_sections_expanded(window, expanded),
            clear_recommendation_review=window.clear_recommendation_review,
            selected_track_controls=window._selected_track_controls,
            apply_song_filter=lambda *args, **kwargs: window._apply_song_filter(*args, **kwargs),
            state_setter=window._replace_app_state,
            export_metadata_status_to_serato=window.export_metadata_status_to_serato,
            undo_manager=window._undo_manager,
            refresh_undo_state=lambda: window._undo_toolbar.refresh(),
            workflow_tab_setter=lambda index: window.workflow_tabs.setCurrentIndex(index),
            open_track=lambda path: (
                window.subprocess.Popen(["open", path])
                if hasattr(window, "subprocess")
                else __import__("xfinaudio.desktop.main_window", fromlist=["subprocess"]).subprocess.Popen(
                    ["open", path]
                )
            ),
            live_load_next=window._live_assistant_screen.load_next,
        ),
        audio_player=window._audio_player,
        sync_state=window._sync_state,
        tr=window.tr,
        log=log,
        parent=window,
    )


def replace_app_state(window, state: AppState) -> None:
    window._state = state
    if hasattr(window, "_app_controller"):
        window._app_controller._state = state
    if hasattr(window, "_dj_readiness_controller"):
        window._dj_readiness_controller._state = state
    if hasattr(window, "_scan_service"):
        window._scan_service._state = state
    if hasattr(window, "_recommendation_service"):
        window._recommendation_service._state = state
    if hasattr(window, "_prep_copilot"):
        window._prep_copilot._state = window


def initialize_app_controller(window, screen_names: list[str]) -> None:
    window._app_controller = AppController(
        state=window._state,
        nav=window._nav,
        workflow_tabs=window.workflow_tabs,
        workflow_sidebar=window.workflow_sidebar,
        screen_names=screen_names,
        screens=AppControllerScreens(
            library=window._library_screen,
            build=window._build_screen,
            review=window._review_screen,
            export=window._export_screen,
            metadata=window._metadata_screen,
            live_assistant=window._live_assistant_screen,
        ),
        view_models=AppControllerViewModels(
            library=window._library_vm,
            build=window._build_vm,
            review=window._review_vm,
            export=window._export_vm,
            metadata=window._metadata_vm,
        ),
        access=AppControllerStateAccess(
            settings=lambda: window.settings,
            is_scanning=lambda: window.current_scan_cancellation_token is not None,
            is_recommending=lambda: window._is_recommending,
            selected_library_paths=lambda: window._library_selected_paths,
            records_by_path=lambda: window._records_by_path,
            scanned_records=lambda: window.scanned_records,
            render_screens=lambda: window._render_screens(),
        ),
    )


def with_defaults(cls, db_path: Path, settings_path: Path | None = None):
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
