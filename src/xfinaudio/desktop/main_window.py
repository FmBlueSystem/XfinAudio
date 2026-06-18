"""PySide6 desktop walking skeleton for XfinAudio."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QCoreApplication, Qt, QTimer, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService, ScanService, TrackPersistence
from xfinaudio.config.settings import AppSettings, ExportSettings, WindowSettings
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.audio_player import AudioPlayer
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.export_coordinator import ExportCoordinator
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.library_filter import metadata_missing_field_records, metadata_status_records
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.live_assistant_coordinator import LiveAssistantCoordinator
from xfinaudio.desktop.menu_builder import MenuBuilder
from xfinaudio.desktop.metadata_view_model import MetadataViewModel
from xfinaudio.desktop.navigation_controller import NavigationController
from xfinaudio.desktop.playlist_coordinator import PlaylistCoordinator
from xfinaudio.desktop.recommendation_controller import RecommendationController
from xfinaudio.desktop.recommendation_coordinator import RecommendationCoordinator
from xfinaudio.desktop.recommendation_presenter import build_recommendation_pool
from xfinaudio.desktop.rendering import (
    _component_score,
    _format_missing_metadata,
    _format_review_score,
    _format_spectral_color,
    _format_track_tags,
    _score_sort_value,
    _table_item,
    _track_review_name,
    format_genre_cell,
    format_genre_sources_tooltip,
    format_quality_summary,
    format_recommendation_warning,
)
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.scan_controller import ScanController
from xfinaudio.desktop.scan_coordinator import ScanCoordinator
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
from xfinaudio.desktop.spectral_completion_worker import SpectralCompletionWorker
from xfinaudio.desktop.status_bar import StatusBar
from xfinaudio.desktop.table_populators import (
    populate_dj_readiness_table,
    populate_library_table,
    populate_transition_review_table,
)
from xfinaudio.desktop.theme import (
    _COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT,
    _COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT,
    _COMPACT_REVIEW_TABLE_MIN_HEIGHT,
    _COMPACT_TABLE_ROW_HEIGHT,
    _DJ_READINESS_TABLE_COLUMN_WIDTHS,
    _DJ_VISUAL_STYLESHEET,
    _READINESS_STATUS_COLORS,
    _READINESS_STATUS_LABELS,
    _READINESS_STATUS_TOOLTIPS,
    _REVIEW_TABLE_COLUMN_WIDTHS,
    _SERATO_EXPORT_HISTORY_COLUMN_WIDTHS,
    _TRACK_TABLE_COLUMN_WIDTHS,
)
from xfinaudio.desktop.undo_manager import Command, UndoManager
from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.scan_service import MetadataScanService, ScanCancellationToken
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.quality.dj_readiness import (
    DjReadinessReport,
    build_dj_readiness_report,
    format_dj_readiness_summary,
    write_dj_readiness_report,
)
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport, build_quality_report
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.prep_copilot import DJSetIntent, PrepCopilotPlan, build_prep_copilot_plan

LOGGER = logging.getLogger(__name__)


class SettingsPersistence(Protocol):
    """Persistence boundary for app settings updates from the desktop UI."""

    def save(self, settings: AppSettings) -> None:
        """Persist application settings."""


_EMPTY_REVIEW_SUMMARY = QCoreApplication.translate("MainWindow", "No recommendation is ready for review.")
_RECOMMENDATION_READY_GUIDANCE = QCoreApplication.translate(
    "MainWindow",
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.",
)
_DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT = 25
_SCREEN_NAMES = ["library", "build", "review", "export", "playlists", "metadata", "live"]
_SIDEBAR_WIDTH_WIDE = 180
_SIDEBAR_WIDTH_NARROW = 120
_NARROW_BREAKPOINT = 900


def responsive_sidebar_width(window_width: int) -> int:
    """Map a window width to the sidebar width: wide above the breakpoint, narrow below."""
    return _SIDEBAR_WIDTH_WIDE if window_width >= _NARROW_BREAKPOINT else _SIDEBAR_WIDTH_NARROW


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


class WorkflowStack(QStackedWidget):
    """QStackedWidget with the tab-like compatibility API used by coordinators/tests."""

    def __init__(self, labels: list[str]) -> None:
        super().__init__()
        self._labels = labels
        self._enabled = [True for _ in labels]

    def tabText(self, index: int) -> str:
        """Return the navigation label for compatibility with the previous QTabWidget."""
        return self._labels[index]

    def setTabEnabled(self, index: int, enabled: bool) -> None:
        """Store per-screen navigation enablement for the sidebar-backed stack."""
        if 0 <= index < len(self._enabled):
            self._enabled[index] = enabled
            screen = self.widget(index)
            if screen is not None:
                screen.setEnabled(enabled)

    def isTabEnabled(self, index: int) -> bool:
        """Return whether a screen can be selected."""
        return 0 <= index < len(self._enabled) and self._enabled[index]

    def setCurrentIndex(self, index: int) -> None:
        """Keep programmatic navigation compatible with the previous workflow_tabs alias."""
        super().setCurrentIndex(index)


class MainWindow(QMainWindow):
    """Main desktop window for the HELP-4 metadata scanning skeleton."""

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

        self._connect_widget_signals()
        self._apply_visual_design()
        self._build_layout()
        self._menu_builder = MenuBuilder(self)  # type: ignore[reportArgumentType]
        self._menu_builder.build(self.menuBar())
        self._restore_window_geometry()
        self._sync_state()

    def closeEvent(self, event: object) -> None:
        """Stop all background threads and audio player before the window is destroyed."""
        self._audio_player.stop()
        self._scan_controller.cancel()
        if self._spectral_completion_worker is not None:
            self._spectral_completion_worker.cancel()
            self._spectral_completion_worker.wait()
            self._spectral_completion_worker = None
        self._recommendation_controller.cancel()
        self._persist_window_geometry()
        super().closeEvent(event)  # type: ignore[arg-type]

    def _build_layout(self) -> None:
        """Assemble widget layout hierarchy, tab pages, and central window container."""
        workflow_labels = [
            self.tr("Library"),
            self.tr("Build Playlist"),
            self.tr("Review Mix"),
            self.tr("Export to Serato"),
            self.tr("My Playlists"),
            self.tr("Metadata Worklist"),
            self.tr("Live Assistant"),
        ]
        self._workflow_labels = workflow_labels
        self.workflow_sidebar = QListWidget()
        self.workflow_sidebar.setObjectName("workflowSidebar")
        self.workflow_sidebar.setAccessibleName(self.tr("Workflow navigation"))
        self.workflow_sidebar.setFixedWidth(_SIDEBAR_WIDTH_WIDE)
        self.workflow_sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for label in workflow_labels:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, label)
            item.setToolTip(label)
            self.workflow_sidebar.addItem(item)

        self.workflow_tabs = WorkflowStack(workflow_labels)
        self.workflow_tabs.addWidget(self._library_screen)
        self.workflow_tabs.addWidget(self._build_screen)
        self.workflow_tabs.addWidget(self._review_screen)
        self.workflow_tabs.addWidget(self._export_screen)
        self.workflow_tabs.addWidget(self._playlists_screen)
        self.workflow_tabs.addWidget(self._metadata_screen)
        self.workflow_tabs.addWidget(self._live_assistant_screen)
        self._current_tab_index = self.workflow_tabs.currentIndex()
        self.workflow_tabs.currentChanged.connect(self._on_tab_changed)
        self.workflow_tabs.currentChanged.connect(self.workflow_sidebar.setCurrentRow)
        self.workflow_sidebar.currentRowChanged.connect(self._on_sidebar_row_changed)
        self.workflow_sidebar.setCurrentRow(0)

        workflow_layout = QHBoxLayout()
        workflow_layout.setContentsMargins(0, 0, 0, 0)
        workflow_layout.setSpacing(10)
        sidebar_panel = QWidget()
        sidebar_panel.setObjectName("workflowSidebarPanel")
        sidebar_panel.setFixedWidth(_SIDEBAR_WIDTH_WIDE)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_layout.addWidget(self.workflow_sidebar, 0)
        sidebar_layout.addStretch(1)
        sidebar_panel.setLayout(sidebar_layout)
        self._sidebar_panel = sidebar_panel
        workflow_layout.addWidget(sidebar_panel)
        workflow_layout.addWidget(self.workflow_tabs, 1)

        layout = QVBoxLayout()
        layout.addLayout(workflow_layout, 1)
        layout.addWidget(self.status_label)
        status_controls = QHBoxLayout()
        status_controls.addWidget(self.status_bar_toggle)
        status_controls.addWidget(self.status_bar, 1)
        layout.addLayout(status_controls)
        self._status_controls_widgets = (self.status_bar_toggle, self.status_bar)
        self._apply_compact_mac_layout(
            layout,
            status_controls,
        )

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _on_sidebar_row_changed(self, index: int) -> None:
        """Navigate from the sidebar while keeping disabled destinations guarded."""
        previous_index = self.workflow_tabs.currentIndex()
        if not self.workflow_tabs.isTabEnabled(index):
            self.workflow_sidebar.setCurrentRow(previous_index)
            return
        self.workflow_tabs.setCurrentIndex(index)
        if self.workflow_tabs.currentIndex() != index:
            self.workflow_sidebar.setCurrentRow(previous_index)

    def resizeEvent(self, event: object) -> None:
        """Adjust the sidebar width and label visibility for the new window width."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._apply_responsive_layout(self.width())

    def _apply_responsive_layout(self, window_width: int) -> None:
        """Resize the sidebar and collapse it to icons on narrow windows (R1, R2)."""
        sidebar_width = responsive_sidebar_width(window_width)
        self._sidebar_panel.setFixedWidth(sidebar_width)
        self.workflow_sidebar.setFixedWidth(sidebar_width)
        collapsed = sidebar_width == _SIDEBAR_WIDTH_NARROW
        for index in range(self.workflow_sidebar.count()):
            item = self.workflow_sidebar.item(index)
            if item is not None:
                item.setText("" if collapsed else self._workflow_labels[index])

    def set_full_screen(self, enabled: bool) -> None:
        """Toggle a distraction-free mode that hides the sidebar and status controls (R3)."""
        self._sidebar_panel.setHidden(enabled)
        for widget in self._status_controls_widgets:
            widget.setHidden(enabled)
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def _restore_window_geometry(self) -> None:
        """Apply persisted window size and position from settings (R4)."""
        window = self.settings.window
        if window.width is not None and window.height is not None:
            self.resize(window.width, window.height)
        if window.x is not None and window.y is not None:
            self.move(window.x, window.y)

    def _persist_window_geometry(self) -> None:
        """Store the current window geometry so the next launch restores it (R4)."""
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
        self.current_scan_cancellation_token: ScanCancellationToken | None = None
        self._is_recommending: bool = False
        self._scan_controller = ScanController(self.workflow_service, parent=self)
        self._recommendation_controller = RecommendationController(self.workflow_service, parent=self)
        self._table_sort_orders: dict[int, Qt.SortOrder] = {}
        self._active_song_search_query = ""
        self._library_selected_paths: list[str] = []
        self._pre_scan_records_by_path: dict[str, TrackRecord] = {}
        self._nav = NavigationController()
        self._undo_manager = UndoManager()
        self._audio_player = AudioPlayer(parent=self)
        self._audio_player.set_volume(self.settings.audio.preview_volume)
        # Playlist DB lives alongside the track DB when possible.
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
        self._scan_coordinator = ScanCoordinator(host=self)  # type: ignore[reportArgumentType]
        self._spectral_completion_worker: SpectralCompletionWorker | None = None
        self._recommendation_coordinator = RecommendationCoordinator(host=self)  # type: ignore[reportArgumentType]
        self._live_assistant_coordinator = LiveAssistantCoordinator(host=self)  # type: ignore[reportArgumentType]
        self._settings_controller = SettingsController(self)  # type: ignore[reportArgumentType]

    def _render_tab(self, index: int, lightweight: bool = False) -> None:
        """Render only the screen mapped to the given tab index.

        Tab indices follow _build_layout addTab order. Indices without a
        render-driven screen (My Playlists, Live Assistant) are intentional
        no-ops, matching the pre-lazy-render behavior.

        Args:
            index: The tab index to render.
            lightweight: If True, skip expensive table population on hidden tabs.
        """
        renderers = {
            0: lambda: self._library_screen.render(self._library_vm, self._state, lightweight=True),
            1: lambda: self._build_screen.render(self._build_vm, self._state, lightweight=lightweight),
            2: lambda: self._review_screen.render(self._review_vm, self._state, lightweight=lightweight),
            3: lambda: self._export_screen.render(self._export_vm, self._state),
            5: lambda: self._metadata_screen.render(self._state, self._metadata_vm, lightweight=lightweight),
        }
        render = renderers.get(index)
        if render is not None:
            render()

    def _refresh_state_fields(self) -> None:
        """Recompute transient AppState fields from the current widget/runtime state."""
        _tab_index = self.workflow_tabs.currentIndex()
        self._state.settings = self.settings
        self._state.is_scanning = self.current_scan_cancellation_token is not None
        self._state.is_recommending = self._is_recommending
        self._state.current_screen = _SCREEN_NAMES[_tab_index] if 0 <= _tab_index < len(_SCREEN_NAMES) else "library"
        self._state.selected_library_paths = list(self._library_selected_paths)

    def _sync_state(self) -> None:
        """Update transient computed fields in _state, then render all screens.

        This keeps every screen consistent with AppState regardless of which tab is
        active, because widgets on non-visible tabs (export-enable state, copilot
        table, recommendation table) are queried and asserted without a tab switch.
        """
        self._refresh_state_fields()
        self._render_screens()

    def _render_screens(self) -> None:
        """Render every screen with current AppState, then refresh tab enablement.

        WHY ALL TABS: This full-sync deliberately iterates every render-driven
        screen — including hidden tabs — because the correctness contract enforced
        by the UI test suite asserts cross-tab state without a tab switch (e.g.
        export-enable state, the recommendation table, and the prep-copilot table
        are queried on hidden tabs right after a state change). Skipping non-visible
        tabs here breaks that contract, so we MUST keep every ViewModel consistent.

        Hidden tabs receive only the lightweight widget updates (button enabled
        states, labels, visibility) that are cheap and side-effect-free; the current
        tab gets the full expensive render including table population. This bounds
        the per-sync cost while preserving cross-tab assertions.

        The real "lazy render" optimization the spec calls for lives in
        _on_tab_changed: routine tab switches do not mutate AppState, so only the
        newly visible screen is rendered there. _sync_state (this path) is the
        correctness path, not the hot path, and must stay a full sync.
        """
        current = self._current_tab_index
        for index in (0, 1, 2, 3, 5):
            self._render_tab(index, lightweight=index != current)
        self._update_tab_states()

    def _on_tab_changed(self, index: int) -> None:
        """Lazily render only the newly visible screen on tab change.

        Routine tab switches do not mutate AppState, so a full _sync_state (which
        re-renders all five screens) is wasteful. Refresh the transient state fields
        (current_screen depends on the active tab) and render only the screen that
        just became visible.
        """
        self._current_tab_index = index
        self._refresh_state_fields()
        self._render_tab(index)

    # ------------------------------------------------------------------
    # AppState property delegates — single source of truth in self._state
    # ------------------------------------------------------------------

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
        """Enable/disable tabs based on NavigationController rules."""
        for index, screen_name in enumerate(_SCREEN_NAMES):
            enabled = self._nav.can_go_to(screen_name, self._state)
            self.workflow_tabs.setTabEnabled(index, enabled)
            screen = self.workflow_tabs.widget(index)
            if screen is not None:
                screen.setEnabled(enabled)
            item = self.workflow_sidebar.item(index)
            if item is not None:
                flags = item.flags() | Qt.ItemFlag.ItemIsEnabled
                if not enabled:
                    flags &= ~Qt.ItemFlag.ItemIsEnabled
                item.setFlags(flags)

    def _build_widgets(self) -> None:
        """Build constructor widgets and intrinsic widget configuration."""
        self.setWindowTitle(self.tr("XfinAudio"))
        self.folder_label = QLabel(self.tr("Library: none"))
        self.library_guidance_label = QLabel(self.tr("Choose a folder to scan metadata."))
        self.recommendation_guidance_label = QLabel(self.tr("Scan metadata before recommending a playlist."))
        self.scan_progress_label = QLabel(self.tr("Scan: idle"))
        self.status_bar = StatusBar(self.folder_label, self.library_guidance_label, self.scan_progress_label)
        self.status_bar.hide()
        self.status_bar_toggle = QPushButton(self.tr("Status"))
        self.status_bar_toggle.setCheckable(True)
        self.status_label = QLabel(self.tr("Ready"))
        self.library_decision_label = QLabel(
            self.tr("DJ Decision Point: choose source, filters, and the track anchor.")
        )
        self.metadata_decision_label = QLabel(
            self.tr("DJ Decision Point: complete missing metadata, then refresh the library.")
        )
        self._library_screen.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._library_screen.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._library_screen.scan_button.setToolTip(self.tr("Scan Metadata (Ctrl+Shift+S)"))
        self._library_screen.missing_column_button.setToolTip(self.tr("Toggle Missing column (Ctrl+M)"))
        self._build_screen.recommend_button.setToolTip(self.tr("Recommend Playlist (Ctrl+R)"))
        self._review_screen.remove_track_button.setToolTip(self.tr("Remove from Playlist (Delete)"))
        self._export_screen.export_button.setToolTip(self.tr("Export to Serato (Ctrl+E)"))
        self.folder_label.setWordWrap(False)
        self.folder_label.setMaximumWidth(220)
        self.library_guidance_label.setWordWrap(False)
        self.library_guidance_label.setMaximumWidth(720)
        self.scan_progress_label.setWordWrap(False)
        self.scan_progress_label.setMaximumWidth(140)
        self.recommendation_guidance_label.setWordWrap(True)
        for label in (self.folder_label, self.library_guidance_label, self.scan_progress_label):
            label.setMaximumHeight(24)
        # Initialize screen labels that depend on settings (not driven by ViewModel)
        self._export_screen.safe_export_folder_label.setText(self._format_safe_export_folder_label())
        self._build_undo_toolbar()

    def _connect_widget_signals(self) -> None:
        """Connect constructor-created widgets to their existing slots and sorting handlers."""
        self._connect_keyboard_shortcuts()
        self._build_screen.copilot_table.itemDoubleClicked.connect(self._apply_prep_copilot_item)
        self._library_screen.tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)
        self._library_screen.search_input.textChanged.connect(self._search_debounce.start)
        self._search_debounce.timeout.connect(lambda: self._apply_song_filter(clear_selection=True))
        self._metadata_screen.status_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self._metadata_screen.missing_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self._metadata_screen.export_button.clicked.connect(lambda: self.export_metadata_status_to_serato())
        self._scan_controller.scan_progress_updated.connect(self._scan_coordinator.on_progress)
        self._scan_controller.scan_completed.connect(self._scan_coordinator.on_completed)
        self._scan_controller.scan_failed.connect(self._scan_coordinator.on_failed)
        self._recommendation_controller.recommendation_completed.connect(self._recommendation_coordinator.on_completed)
        self._recommendation_controller.recommendation_failed.connect(self._recommendation_coordinator.on_failed)
        # LibraryScreen signals
        self._library_screen.folder_change_requested.connect(self.choose_folder)
        self._library_screen.scan_requested.connect(self.scan_selected_folder)
        self._library_screen.cancel_scan_requested.connect(self.cancel_scan)
        self.status_bar_toggle.toggled.connect(self._set_status_bar_visible)
        self._library_screen.selection_changed.connect(self._on_library_selection_changed)
        self._library_screen.metadata_screen_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(5))
        self._library_screen.proceed_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(1))
        self._library_screen.settings_requested.connect(self._open_settings_dialog)
        self._library_screen.filters_cleared.connect(self._on_library_filters_cleared)
        # BuildScreen signals
        self._build_screen.recommend_requested.connect(self._on_recommend_requested)
        self._build_screen.spectral_cohesion_changed.connect(self._on_spectral_cohesion_changed)
        self._build_screen.copilot_generate_requested.connect(self.generate_prep_copilot)
        self._build_screen.copilot_variant_applied.connect(self._on_copilot_variant_applied)
        self._build_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(0))
        self._build_screen.proceed_button.clicked.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        self._build_screen.exclude_requested.connect(self._on_exclude_requested)
        self._build_screen.lock_requested.connect(self._on_lock_requested)
        self._build_screen.clear_constraints_requested.connect(self._on_clear_constraints)
        # ReviewScreen signals
        self._review_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(1))
        self._review_screen.proceed_to_export_requested.connect(self._on_proceed_to_export)
        self._review_screen.track_remove_requested.connect(self._on_track_remove_requested)
        self._review_screen.track_play_requested.connect(self._on_track_play_requested)
        # LibraryScreen play signal
        self._library_screen.track_play_requested.connect(self._on_track_play_requested)
        # Audio preview signals
        self._library_screen.play_requested.connect(self._on_preview_play_requested)
        self._library_screen.pause_requested.connect(self._audio_player.pause)
        self._audio_player.state_changed.connect(self._on_player_state_changed)
        self._audio_player.error_occurred.connect(self._on_player_error)
        # ExportScreen signals
        self._export_screen.preview_requested.connect(self.preview_export)
        self._export_screen.export_requested.connect(self.export_recommendation)
        self._export_screen.readiness_export_requested.connect(lambda: self.export_dj_readiness_report())
        self._export_screen.safe_folder_change_requested.connect(self.choose_safe_export_folder)
        self._export_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        # MetadataScreen signals
        self._metadata_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(0))
        self._metadata_screen.filter_changed.connect(self._sync_state)
        self._metadata_screen.export_requested.connect(self._on_metadata_export_requested)
        # LiveAssistantScreen signals
        self._live_assistant_coordinator.connect_signals()
        # Playlist signals (MyPlaylistsScreen + PlaylistEditor) — owned by PlaylistCoordinator
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
        """Bind global keyboard shortcuts for the main workflow actions.

        Shortcuts are kept alive in self._keyboard_shortcuts so tests and
        introspection can reference them without relying on focus-dependent
        key events.
        """
        shortcuts = [
            ("open_folder", QKeySequence.StandardKey.Open, self.choose_folder),
            ("focus_search", QKeySequence("Ctrl+F"), self._library_screen.search_input.setFocus),
            ("scan_metadata", QKeySequence("Ctrl+Shift+S"), self.scan_selected_folder),
            ("recommend_playlist", QKeySequence("Ctrl+R"), self._build_screen.recommend_button.click),
            ("export_recommendation", QKeySequence("Ctrl+E"), self._export_screen.export_button.click),
            ("toggle_missing_column", QKeySequence("Ctrl+M"), self._library_screen.missing_column_button.click),
            ("open_selected_track", QKeySequence("Return"), self._open_selected_library_track),
            ("remove_selected_track", QKeySequence("Del"), self._remove_selected_review_track),
            ("cancel_scan", QKeySequence("Esc"), self.cancel_scan),
            ("undo", QKeySequence("Ctrl+Z"), self.undo),
            ("redo", QKeySequence("Ctrl+Shift+Z"), self.redo),
        ]
        self._keyboard_shortcuts: dict[str, QShortcut] = {}
        for name, sequence, slot in shortcuts:
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(slot)
            self._keyboard_shortcuts[name] = shortcut

    def _build_undo_toolbar(self) -> None:
        """Add a toolbar with undo/redo buttons and an undo-history dropdown (R5, R6)."""
        toolbar = QToolBar(self.tr("Undo/Redo"))
        toolbar.setObjectName("undoRedoToolbar")
        self.addToolBar(toolbar)
        self.undo_button = QPushButton(self.tr("Undo"))
        self.undo_button.setObjectName("undoButton")
        self.undo_button.setToolTip(self.tr("Undo last action (Ctrl+Z)"))
        self.undo_button.clicked.connect(self.undo)
        self.undo_history_menu = QMenu(self.undo_button)
        self.undo_button.setMenu(self.undo_history_menu)
        self.redo_button = QPushButton(self.tr("Redo"))
        self.redo_button.setObjectName("redoButton")
        self.redo_button.setToolTip(self.tr("Redo last undone action (Ctrl+Shift+Z)"))
        self.redo_button.clicked.connect(self.redo)
        toolbar.addWidget(self.undo_button)
        toolbar.addWidget(self.redo_button)
        self._refresh_undo_state()

    def undo(self) -> None:
        """Undo the most recent reversible action."""
        self._undo_manager.undo()
        self._refresh_undo_state()

    def redo(self) -> None:
        """Redo the most recently undone action."""
        self._undo_manager.redo()
        self._refresh_undo_state()

    def _refresh_undo_state(self) -> None:
        """Sync toolbar button enablement and the history dropdown with the undo stack."""
        self.undo_button.setEnabled(self._undo_manager.can_undo)
        self.redo_button.setEnabled(self._undo_manager.can_redo)
        self.undo_history_menu.clear()
        for label in self._undo_manager.history():
            self.undo_history_menu.addAction(label)

    def _open_selected_library_track(self) -> None:
        """Open the first selected library track in the system default player."""
        selected_rows = sorted({index.row() for index in self._library_screen.tracks_table.selectedIndexes()})
        if not selected_rows:
            return
        path_item = self._library_screen.tracks_table.item(selected_rows[0], _TRACK_PATH_COLUMN)
        if path_item is not None:
            self._on_track_play_requested(path_item.text())

    def _remove_selected_review_track(self) -> None:
        """Remove the selected review track from the session playlist."""
        row = self._review_screen.recommendation_table.currentRow()
        path_item = self._review_screen.recommendation_table.item(row, 0)
        if path_item is not None and (path := path_item.data(Qt.ItemDataRole.UserRole)):
            self._on_track_remove_requested(path)

    def _apply_compact_mac_layout(
        self,
        layout: QVBoxLayout,
        status_controls: QHBoxLayout,
    ) -> None:
        """Use dense desktop spacing so the library browser does not dominate MacBook screens."""
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        status_controls.setSpacing(8)

        self._build_screen.recommend_button.setMinimumWidth(220)
        self._build_screen.recommend_button.setMaximumWidth(260)
        self._build_screen.copilot_button.setMinimumWidth(190)
        self._build_screen.copilot_button.setMaximumWidth(220)
        self._build_screen.apply_variant_button.setMaximumWidth(220)
        self._build_screen.genre_focus_input.setMinimumWidth(160)
        self._build_screen.genre_focus_input.setMaximumWidth(360)
        self._metadata_screen.status_combo.setMaximumWidth(170)
        self._metadata_screen.missing_combo.setMaximumWidth(220)
        self._metadata_screen.export_button.setMaximumWidth(220)

        self._library_screen.tracks_table.setMinimumHeight(400)
        self._library_screen.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._review_screen.transition_table.setMinimumHeight(_COMPACT_REVIEW_TABLE_MIN_HEIGHT)
        self._review_screen.transition_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._review_screen.readiness_table.setMaximumHeight(_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT)
        self._review_screen.readiness_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._export_screen.history_table.setMaximumHeight(_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT)
        self._export_screen.history_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_compact_table_columns()
        self._set_recommendation_sections_expanded(False)

    def _set_status_bar_visible(self, visible: bool) -> None:
        """Show or hide the compact status bar from the toggle button."""
        self.status_bar.setVisible(visible)
        self.status_bar_toggle.setChecked(visible)

    def show_status_bar(self) -> None:
        """Reveal the compact status bar for scan activity."""
        self._set_status_bar_visible(True)

    def _apply_compact_table_columns(self) -> None:
        """Allocate readable column widths while letting path/warning columns absorb spare space."""
        table_widths = (
            (self._library_screen.tracks_table, _TRACK_TABLE_COLUMN_WIDTHS),
            (self._review_screen.transition_table, _REVIEW_TABLE_COLUMN_WIDTHS),
            (self._review_screen.readiness_table, _DJ_READINESS_TABLE_COLUMN_WIDTHS),
            (self._export_screen.history_table, _SERATO_EXPORT_HISTORY_COLUMN_WIDTHS),
        )
        for table, widths in table_widths:
            for column_index, width in enumerate(widths):
                table.horizontalHeader().setSectionResizeMode(column_index, QHeaderView.ResizeMode.Interactive)
                table.setColumnWidth(column_index, width)
            table.horizontalHeader().setStretchLastSection(True)

    def _apply_visual_design(self) -> None:
        """Apply a DJ-focused dark visual theme with clear action hierarchy."""
        self._build_screen.recommend_button.setObjectName("primaryAction")
        self._library_screen.search_input.setObjectName("songSearch")
        self.status_label.setObjectName("statusLabel")
        for label in (
            self.folder_label,
            self.library_guidance_label,
            self.scan_progress_label,
            self.recommendation_guidance_label,
            self._export_screen.export_guidance_label,
            self._export_screen.safe_export_folder_label,
            self.library_decision_label,
            self.metadata_decision_label,
        ):
            label.setObjectName("guidanceLabel")
        for table in (
            self._library_screen.tracks_table,
            self._review_screen.transition_table,
            self._review_screen.readiness_table,
            self._export_screen.history_table,
        ):
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.setWordWrap(False)
            table.verticalHeader().setDefaultSectionSize(_COMPACT_TABLE_ROW_HEIGHT)
            table.verticalHeader().setMinimumSectionSize(_COMPACT_TABLE_ROW_HEIGHT)
            table.verticalHeader().setVisible(False)
        self._library_screen.search_input.setClearButtonEnabled(True)
        self.setStyleSheet(_DJ_VISUAL_STYLESHEET)

    def _set_recommendation_sections_expanded(self, expanded: bool) -> None:
        """Give vertical space back to browsing until a recommendation exists."""
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
        """Make table headers clickable without enabling disruptive always-on sorting."""
        header = table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(lambda column, table=table: self._sort_table_by_column(table, column))

    def _sort_table_by_column(self, table: QTableWidget, column: int) -> None:
        """Sort a table column and toggle order on repeated clicks."""
        sort_key = id(table) * 1000 + column
        previous_order = self._table_sort_orders.get(sort_key)
        order = (
            Qt.SortOrder.DescendingOrder
            if previous_order == Qt.SortOrder.AscendingOrder
            else Qt.SortOrder.AscendingOrder
        )
        self._table_sort_orders.clear()
        self._table_sort_orders[sort_key] = order
        table.sortItems(column, order)
        table.horizontalHeader().setSortIndicator(column, order)
        if table is self._library_screen.tracks_table:
            self._apply_song_filter(clear_selection=False)

    @classmethod
    def with_defaults(cls, db_path: Path, settings_path: Path | None = None) -> MainWindow:
        """Create a window wired to the default scan service, repository, and settings file."""
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
        """Return display text for the configured safe export folder."""
        folder = self.settings.export.safe_export_folder
        if folder is None:
            return self.tr("No safe export folder selected")
        return self.tr("Safe export folder: {0}").format(folder)

    def choose_folder(self) -> None:
        """Open a folder picker and store the selected library folder."""
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose music folder"))
        if folder:
            self.set_selected_folder(Path(folder))

    def set_selected_folder(self, folder: Path) -> None:
        """Set the current folder and update the display label."""
        self.selected_folder = folder
        self._persist_last_scan_folder(folder)
        self._clear_scan_dependent_state()
        self.folder_label.setText(str(folder))
        self.library_guidance_label.setText(
            self.tr("Folder selected. Scan metadata to find complete Mixed In Key tracks.")
        )
        self.recommendation_guidance_label.setText(self.tr("Scan metadata before recommending a playlist."))
        self._refresh_idle_action_state()
        self.status_label.setText(self.tr("Folder selected"))
        self._sync_state()

    def _persist_last_scan_folder(self, folder: Path) -> None:
        """Persist the latest scan folder so saved libraries can be refreshed after restart."""
        self.settings = self.settings.model_copy(
            update={
                "library": self.settings.library.model_copy(update={"last_scan_folder": folder}),
            }
        )
        if self.settings_repository is not None:
            self.settings_repository.save(self.settings)

    def _populate_track_table(self, records: list[TrackRecord]) -> None:
        """Populate the library table in source order, then re-apply the active filter."""
        self._records_by_path = populate_library_table(
            self._library_screen.tracks_table,
            records,
            item_factory=_table_item,
            format_missing_metadata=_format_missing_metadata,
            format_track_tags=_format_track_tags,
            format_spectral_color=_format_spectral_color,
            format_genre_cell=format_genre_cell,
            format_genre_tooltip=format_genre_sources_tooltip,
        )
        self._apply_song_filter(clear_selection=False)

    def _apply_song_filter(self, query: str | None = None, *, clear_selection: bool = False) -> None:
        """Hide library rows whose song title/status does not match active browse filters."""
        search_query = (self._library_screen.search_input.text() if query is None else query).strip().casefold()
        if clear_selection and search_query != self._active_song_search_query:
            self._library_screen.tracks_table.clearSelection()
        self._active_song_search_query = search_query
        status_filter = self._selected_metadata_status_filter()
        missing_filter = self._selected_missing_metadata_filter()
        for row_index in range(self._library_screen.tracks_table.rowCount()):
            title_item = self._library_screen.tracks_table.item(row_index, _TRACK_TITLE_COLUMN)
            title = "" if title_item is None else title_item.text().casefold()
            status_item = self._library_screen.tracks_table.item(row_index, _TRACK_STATUS_COLUMN)
            status = "" if status_item is None else status_item.text()
            path_item = self._library_screen.tracks_table.item(row_index, _TRACK_PATH_COLUMN)
            path = "" if path_item is None else path_item.text()
            record = self._records_by_path.get(path)
            title_mismatch = bool(search_query) and search_query not in title
            status_mismatch = status_filter is not None and status != status_filter
            missing_mismatch = missing_filter is not None and (
                record is None or missing_filter not in record.missing_required_fields
            )
            self._library_screen.tracks_table.setRowHidden(
                row_index,
                title_mismatch or status_mismatch or missing_mismatch,
            )
        self._refresh_idle_action_state()

    def _selected_metadata_status_filter(self) -> str | None:
        """Return the active complete/incomplete filter, or None for all statuses."""
        status_text = self._metadata_screen.status_combo.currentText().casefold()
        return status_text if status_text in {"complete", "incomplete"} else None

    def _selected_missing_metadata_filter(self) -> str | None:
        """Return the active missing-field audit filter, or None for all missing fields."""
        return _MISSING_METADATA_FILTERS.get(self._metadata_screen.missing_combo.currentText())

    def _metadata_status_records(self, status: str) -> list[TrackRecord]:
        """Return records matching the requested metadata status."""
        return metadata_status_records(self.scanned_records, status)

    def _metadata_missing_field_records(self, missing_field: str) -> list[TrackRecord]:
        """Return incomplete records missing the requested metadata field."""
        return metadata_missing_field_records(self.scanned_records, missing_field)

    def restore_persisted_tracks(self, records: list[TrackRecord]) -> None:
        """Restore app-owned persisted tracks into the visible desktop session."""
        if not records:
            self._refresh_idle_action_state()
            return
        self.scanned_records = records
        complete_count = sum(1 for record in records if record.metadata_status == "complete")
        incomplete_count = len(records) - complete_count
        self._populate_track_table(records)
        if self.selected_folder is None:
            self.folder_label.setText(self.tr("Library: saved"))
            self.folder_label.setToolTip(self.tr("Saved library loaded; no scan folder selected."))
            self.library_guidance_label.setText(self.tr("Use filters/search, select a complete track, then recommend."))
            self.library_guidance_label.setToolTip(
                self.tr("Showing saved library from the app database. Choose a folder to re-scan or update metadata.")
            )
        else:
            self.folder_label.setText(self.tr("Library: saved folder"))
            self.folder_label.setToolTip(self.tr("Saved library loaded: {0}").format(self.selected_folder))
            self.library_guidance_label.setText(self.tr("Use filters/search, select a complete track, then recommend."))
            self.library_guidance_label.setToolTip(
                self.tr("Saved library loaded. Click Scan Metadata to refresh metadata from the last folder.")
            )
        self.recommendation_guidance_label.setText(_RECOMMENDATION_READY_GUIDANCE)
        self.status_label.setText(
            self.tr("Loaded saved library: {0} complete, {1} incomplete").format(complete_count, incomplete_count)
        )
        self._refresh_idle_action_state()
        self._sync_state()
        self._start_spectral_completion_worker(records)

    def _start_spectral_completion_worker(self, records: list[TrackRecord]) -> None:
        """Start background spectral color completion for records missing a profile."""
        missing = [record for record in records if record.spectral_profile is None]
        if not missing:
            return
        total_count = len(missing)
        self._cancel_spectral_completion_worker()
        self._state = self._state.model_copy(
            update={
                "is_completing_spectral": True,
                "spectral_progress_count": 0,
                "spectral_total_count": total_count,
            }
        )
        self._sync_state()
        worker = SpectralCompletionWorker(parent=self)
        worker.progress.connect(self._on_spectral_profile_ready)
        worker.progress_updated.connect(self._on_spectral_progress_updated)
        worker.finished.connect(self._on_spectral_completion_finished)
        worker.failed.connect(lambda error: LOGGER.error("Spectral completion failed: %s", error))
        self._spectral_completion_worker = worker
        repository = self.workflow_service.repository
        worker.start(missing, repository)

    def _cancel_spectral_completion_worker(self) -> None:
        """Cancel any running spectral completion worker."""
        if self._spectral_completion_worker is not None:
            self._spectral_completion_worker.cancel()
            self._spectral_completion_worker = None
        if self._state.is_completing_spectral:
            self._state = self._state.model_copy(
                update={
                    "is_completing_spectral": False,
                    "spectral_progress_count": 0,
                    "spectral_total_count": 0,
                }
            )
            self._sync_state()

    @Slot(int, int)
    def _on_spectral_progress_updated(self, processed_count: int, total_count: int) -> None:
        """Update library status while background spectral completion runs."""
        self._state = self._state.model_copy(
            update={
                "is_completing_spectral": True,
                "spectral_progress_count": processed_count,
                "spectral_total_count": total_count,
            }
        )
        self._sync_state()

    @Slot(str, object)
    def _on_spectral_profile_ready(self, path: str, profile: object) -> None:
        """Update a single track's color cell when its spectral profile is ready."""
        for index, record in enumerate(self.scanned_records):
            if record.path == path:
                self.scanned_records[index] = record.model_copy(update={"spectral_profile": profile})
                break
        if path in self._records_by_path:
            existing = self._records_by_path[path]
            self._records_by_path[path] = existing.model_copy(update={"spectral_profile": profile})
        for row_index in range(self._library_screen.tracks_table.rowCount()):
            path_item = self._library_screen.tracks_table.item(row_index, _TRACK_PATH_COLUMN)
            if path_item is not None and path_item.text() == path:
                record = self._records_by_path.get(path)
                color_text = _format_spectral_color(record) if record is not None else ""
                self._library_screen.tracks_table.item(row_index, _TRACK_COLOR_COLUMN).setText(color_text)
                break
        self._sync_state()

    @Slot()
    def _on_spectral_completion_finished(self) -> None:
        """Clear the worker reference when the background worker finishes."""
        self._spectral_completion_worker = None
        self._state = self._state.model_copy(
            update={
                "is_completing_spectral": False,
                "spectral_progress_count": 0,
                "spectral_total_count": 0,
            }
        )
        self._sync_state()

    def _clear_scan_dependent_state(self) -> None:
        """Clear scan and recommendation results that belong to a previous folder."""
        self.scanned_records = []
        self._records_by_path = {}
        self.last_recommendation = None
        self.last_playlist_explanation = None
        self.last_quality_report = None
        self.last_dj_readiness_report = None
        self.last_prep_copilot_plan = None
        self._set_applied_copilot_variant(None)
        self._library_screen.tracks_table.setRowCount(0)
        self._library_screen.search_input.clear()
        self._review_screen.recommendation_table.setRowCount(0)
        self._set_recommendation_sections_expanded(False)
        self.clear_recommendation_review()
        self._export_screen.export_guidance_label.setText(
            self.tr(
                "Review recommendations before exporting. "
                "Serato export is enabled only after a recommendation is ready."
            )
        )

        self._sync_state()

    def _refresh_idle_action_state(self) -> None:
        """Enable only the actions that are valid for the current idle UI state."""
        self._library_screen.scan_button.setEnabled(self.selected_folder is not None)
        self._build_screen.recommend_button.setEnabled(self._selected_track_controls() is not None)
        status_filter = self._selected_metadata_status_filter()
        missing_filter = self._selected_missing_metadata_filter()
        self._metadata_screen.export_button.setEnabled(
            (missing_filter is not None and bool(self._metadata_missing_field_records(missing_filter)))
            or (status_filter is not None and bool(self._metadata_status_records(status_filter)))
        )
        self._library_screen.cancel_button.setEnabled(False)

    def choose_safe_export_folder(self) -> None:
        """Open a folder picker and store the selected safe export folder."""
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose safe export folder"))
        if folder:
            self.set_safe_export_folder(Path(folder))

    def _open_settings_dialog(self) -> None:
        """Open the settings dialog and apply changes if confirmed."""
        self._settings_controller.open_dialog()

    def _on_spectral_cohesion_changed(self, value: int) -> None:
        """Persist spectral cohesion when the Build Playlist slider moves."""
        cohesion = value / 100.0
        self.settings = self.settings.model_copy(
            update={"scoring": self.settings.scoring.model_copy(update={"spectral_cohesion": cohesion})}
        )
        if self.settings_repository is not None:
            self.settings_repository.save(self.settings)
        self._sync_state()

    def _apply_settings(self, new_settings: AppSettings) -> None:
        """Apply and persist settings from the settings dialog."""
        self._settings_controller.apply(new_settings)

    def set_safe_export_folder(self, folder: Path) -> None:
        """Persist a safe export folder if it is not the selected audio folder."""
        if self.selected_folder is not None and folder == self.selected_folder:
            self.status_label.setText(self.tr("Safe export folder must be outside the selected audio folder"))
            return

        self.settings = self.settings.model_copy(update={"export": ExportSettings(safe_export_folder=folder)})
        if self.settings_repository is not None:
            self.settings_repository.save(self.settings)
        self._export_screen.safe_export_folder_label.setText(self._format_safe_export_folder_label())
        self.status_label.setText(self.tr("Safe export folder selected"))

        self._sync_state()

    def export_dj_readiness_report(self, *, generated_at: datetime | None = None) -> None:
        """Export the latest DJ readiness report as JSON and CSV audit artifacts."""
        if self.last_dj_readiness_report is None:
            self.status_label.setText(self.tr("Generate a recommendation before exporting DJ readiness"))
            return
        safe_folder = self.settings.export.safe_export_folder
        if safe_folder is None:
            self.status_label.setText(self.tr("Choose a safe export folder before exporting DJ readiness"))
            return
        generated_at = generated_at or datetime.now()
        timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
        json_path = safe_folder / f"xfinaudio-dj-readiness-{timestamp}.json"
        csv_path = safe_folder / f"xfinaudio-dj-readiness-{timestamp}.csv"
        json_path, csv_path = write_dj_readiness_report(self.last_dj_readiness_report, json_path, csv_path)
        self.status_label.setText(self.tr("Exported DJ readiness report: {0} and {1}").format(json_path, csv_path))

    def preview_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Preview the export destination for the selected DJ software."""
        self._export_coordinator.preview_export(
            serato_folder=serato_folder, crate_name=crate_name, generated_at=generated_at
        )

    def export_recommendation(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Export the current recommendation to the selected DJ software."""
        self._export_coordinator.export_recommendation(
            serato_folder=serato_folder, crate_name=crate_name, generated_at=generated_at
        )

    def preview_serato_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Preview the Serato crate destination without writing files."""
        self._export_coordinator.preview_serato_export(
            serato_folder=serato_folder, crate_name=crate_name, generated_at=generated_at
        )

    def export_recommendation_to_serato(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Export the current recommendation as a confirmed Serato crate."""
        self._export_coordinator.export_recommendation_to_serato(
            serato_folder=serato_folder, crate_name=crate_name, generated_at=generated_at
        )

    def export_metadata_status_to_serato(
        self,
        *,
        status: str | None = None,
        missing_field: str | None = None,
        serato_folder: Path | None = None,
    ) -> None:
        """Export complete or incomplete metadata worklists as Serato crates."""
        self._export_coordinator.export_metadata_status_to_serato(
            status=status, missing_field=missing_field, serato_folder=serato_folder
        )

    def scan_selected_folder(self) -> None:
        """Scan the selected folder, persist records, and refresh table/status widgets."""
        self._scan_coordinator.scan_selected_folder()

    def _begin_scan_state(self) -> None:
        """Prepare synchronous scan state and enable cooperative cancellation."""
        self._scan_coordinator.begin_scan_state()

    def _on_library_selection_changed(self, paths: list[str]) -> None:
        """Update state when user selection changes in LibraryScreen."""
        self._library_selected_paths = paths
        self._refresh_idle_action_state()
        # Stop preview if selection changed to a different track
        if self._audio_player._source_path is not None and self._audio_player._source_path not in paths:
            self._audio_player.stop()

    def cancel_scan(self) -> None:
        """Request cancellation for the current scan."""
        self._scan_coordinator.cancel()

    def show_tracks(
        self,
        records: list[TrackRecord],
        complete_count: int | None = None,
        incomplete_count: int | None = None,
    ) -> None:
        """Render scanned records in the desktop table."""
        self._populate_track_table(records)
        if complete_count is None:
            complete_count = sum(1 for record in records if record.metadata_status == "complete")
        if incomplete_count is None:
            incomplete_count = len(records) - complete_count
        self.status_label.setText(
            self.tr("Scan complete: {0} complete, {1} incomplete").format(complete_count, incomplete_count)
        )
        self._sync_state()
        self._start_spectral_completion_worker(records)

    def generate_prep_copilot(self) -> None:
        """Generate comparable DJ Prep Copilot variants from current selection and intent controls."""
        controls = self._selected_track_controls()
        if controls is None:
            self.last_prep_copilot_plan = None
            self._build_screen.copilot_table.setRowCount(0)
            self._build_screen.apply_variant_button.setEnabled(False)
            self.status_label.setText(self.tr("Select at least one complete track before generating Prep Copilot"))
            return
        records = self._desktop_recommendation_records(controls)
        genre_focus = self._build_screen.genre_focus_input.text().strip() or None
        intent = DJSetIntent(
            name="Desktop Prep Copilot",
            strategy=self._build_screen.strategy_combo.currentText(),
            target_track_count=self._build_screen.target_count_input.value(),
            start_path=controls.start_path,
            required_paths=controls.manual_order_paths,
            genre_focus=genre_focus,
        )
        plan = build_prep_copilot_plan(records, intent)
        self.last_prep_copilot_plan = plan
        self._build_screen.apply_variant_button.setEnabled(True)
        self.status_label.setText(self.tr("Generated {0} Prep Copilot variant(s)").format(len(plan.variants)))
        # Full-render the Build screen so its copilot table is populated from the
        # plan now stored in AppState, even though Build may be a hidden tab. The
        # copilot table is cross-tab state that tests assert without a tab switch,
        # so we cannot rely on _render_screens' lightweight path for it. _sync_state
        # then keeps every other screen consistent.
        self._build_screen.copilot_table.setHidden(len(plan.variants) == 0)
        self._build_screen.render(self._build_vm, self._state)
        self._sync_state()

    def _apply_prep_copilot_item(self, item: QTableWidgetItem) -> None:
        """Apply the Prep Copilot variant represented by a double-clicked table item."""
        self._build_screen.copilot_table.selectRow(item.row())
        self.apply_selected_prep_copilot_variant()

    def apply_selected_prep_copilot_variant(self) -> None:
        """Apply the selected Prep Copilot variant to the main review/export flow."""
        if self.last_prep_copilot_plan is None:
            self.status_label.setText(self.tr("Generate and select a Prep Copilot variant before applying"))
            return
        selected_rows = sorted({index.row() for index in self._build_screen.copilot_table.selectedIndexes()})
        if not selected_rows:
            self.status_label.setText(self.tr("Generate and select a Prep Copilot variant before applying"))
            return
        row_index = selected_rows[0]
        if row_index >= len(self.last_prep_copilot_plan.variants):
            self.status_label.setText(self.tr("Generate and select a Prep Copilot variant before applying"))
            return
        variant = self.last_prep_copilot_plan.variants[row_index]
        recommendation = variant.recommendation
        explanation = build_playlist_explanation(recommendation)
        quality_report = build_quality_report(recommendation)
        self.last_recommendation = recommendation
        self.last_playlist_explanation = explanation
        self.last_quality_report = quality_report
        self.last_dj_readiness_report = variant.readiness
        self._state.playlist_removed_paths = frozenset()
        self._sync_state()
        self._set_applied_copilot_variant(variant.name)
        self.show_recommendation(recommendation.ordered_tracks, recommendation.strategy.name, explanation)
        self._review_screen.review_summary_label.setText(format_quality_summary(quality_report))
        self._review_screen.dj_readiness_label.setText(format_dj_readiness_summary(variant.readiness))
        self._populate_dj_readiness_table(variant.readiness)
        self.show_transition_review(explanation)
        self._export_screen.export_guidance_label.setText(
            self.tr("Inspect the selected Prep Copilot variant before exporting it to Serato.")
        )
        self.status_label.setText(self.tr("Applied Prep Copilot variant: {0}").format(variant.name))

    def _set_applied_copilot_variant(self, variant_name: str | None) -> None:
        """Update applied Copilot variant state and export badge."""
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
        """Generate and display a playlist recommendation from scanned records."""
        self._recommendation_coordinator.recommend()

    def _selected_track_controls(self) -> DJControls | None:
        """Convert selected track rows into DJ sequencing controls.

        Prefers paths reported by LibraryScreen (visible selection). Falls back to
        the legacy tracks_table widget for test compatibility.
        """
        records_by_path = {record.path: record for record in self.scanned_records}

        # Primary source: paths emitted by LibraryScreen.selection_changed
        if self._library_selected_paths:
            selected_records: list[TrackRecord] = []
            seen_paths: set[str] = set()
            for path in self._library_selected_paths:
                record = records_by_path.get(path)
                if record is None or record.metadata_status != "complete" or path in seen_paths:
                    continue
                selected_records.append(record)
                seen_paths.add(path)
            if selected_records:
                if len(selected_records) == 1:
                    return DJControls(
                        start_path=selected_records[0].path,
                        excluded_paths=self._state.excluded_paths,
                        locked_paths=self._state.locked_paths,
                    )
                return DJControls(
                    manual_order_paths=[r.path for r in selected_records],
                    excluded_paths=self._state.excluded_paths,
                    locked_paths=self._state.locked_paths,
                )

        # Fallback: legacy widget used by automated tests
        selected_rows = sorted({index.row() for index in self._library_screen.tracks_table.selectedIndexes()})
        selected_records = []
        seen_paths = set()
        for row in selected_rows:
            if self._library_screen.tracks_table.isRowHidden(row):
                continue
            path_item = self._library_screen.tracks_table.item(row, _TRACK_PATH_COLUMN)
            if path_item is None:
                continue
            record = records_by_path.get(path_item.text())
            if record is None or record.metadata_status != "complete" or record.path in seen_paths:
                continue
            selected_records.append(record)
            seen_paths.add(record.path)
        if not selected_records:
            return None
        if len(selected_records) == 1:
            return DJControls(
                start_path=selected_records[0].path,
                excluded_paths=self._state.excluded_paths,
                locked_paths=self._state.locked_paths,
            )
        return DJControls(
            manual_order_paths=[record.path for record in selected_records],
            excluded_paths=self._state.excluded_paths,
            locked_paths=self._state.locked_paths,
        )

    def _desktop_recommendation_records(self, controls: DJControls | None) -> list[TrackRecord]:
        """Return an interactive-size recommendation pool while preserving selected control tracks."""
        return build_recommendation_pool(self.scanned_records, controls, _DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT)

    def _begin_recommendation_state(self, candidate_count: int) -> None:
        self._recommendation_coordinator._begin_recommendation_state(candidate_count)

    def _end_recommendation_state(self) -> None:
        self._recommendation_coordinator._end_recommendation_state()

    def _start_recommendation_worker(
        self, records: list[TrackRecord], strategy_name: str, controls: DJControls | None = None
    ) -> None:
        self._recommendation_coordinator._start_recommendation_worker(records, strategy_name, controls)

    @Slot(object)
    def _finish_recommendation(self, result: Any) -> None:
        """Render a completed background recommendation."""
        self._recommendation_coordinator.on_completed(result)

    @Slot(object)
    def _fail_recommendation(self, error: object) -> None:
        """Recover the UI if background recommendation generation fails."""
        self._recommendation_coordinator.on_failed(error)

    def show_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        explanation: PlaylistExplanation | None = None,
    ) -> None:
        """Update expand/collapse state and re-render the recommendation table via the VM.

        Note: _sync_state() only renders the current tab (lightweight mode), so we
        explicitly render tab 2 (ReviewScreen) to populate the recommendation table
        since state.last_recommendation is already set by _finish_recommendation.
        """
        self._set_recommendation_sections_expanded(bool(records))
        self._sync_state()
        # Ensure recommendation table is populated even though we're not on tab 2
        self._render_tab(2)

    def clear_recommendation_review(self) -> None:
        """Reset recommendation review widgets to their empty state."""
        self._review_screen.review_summary_label.setText(_EMPTY_REVIEW_SUMMARY)
        self._review_screen.dj_readiness_label.setText(self.tr("DJ Readiness: No recommendation ready."))
        self._review_screen.readiness_table.setRowCount(0)
        self._review_screen.transition_table.setRowCount(0)
        self._build_screen.copilot_table.setHidden(True)
        if self._review_screen.recommendation_table.rowCount() == 0:
            self._set_recommendation_sections_expanded(False)

    def _show_dj_readiness(
        self,
        recommendation: PlaylistRecommendation,
        quality_report: RecommendationQualityReport,
        *,
        serato_plan: Any | None = None,
        serato_volume_root: Path | None = None,
    ) -> None:
        """Render operational DJ readiness for the current recommendation."""
        report = build_dj_readiness_report(
            recommendation,
            quality_report,
            serato_plan=serato_plan,
            serato_volume_root=serato_volume_root,
        )
        self.last_dj_readiness_report = report
        self._sync_state()
        self._review_screen.dj_readiness_label.setText(format_dj_readiness_summary(report))
        self._populate_dj_readiness_table(report)

    def _populate_dj_readiness_table(self, report: DjReadinessReport) -> None:
        """Render actionable readiness checks in a compact table."""
        populate_dj_readiness_table(
            self._review_screen.readiness_table,
            report,
            item_factory=_table_item,
            readiness_status_labels=_READINESS_STATUS_LABELS,
            readiness_status_colors=_READINESS_STATUS_COLORS,
            readiness_status_tooltips=_READINESS_STATUS_TOOLTIPS,
        )

    def show_transition_review(self, explanation: PlaylistExplanation) -> None:
        """Render transition component scores and warnings in the review table."""
        populate_transition_review_table(
            self._review_screen.transition_table,
            explanation,
            item_factory=_table_item,
            format_review_score=_format_review_score,
            component_score=_component_score,
            score_sort_value=_score_sort_value,
            track_review_name=_track_review_name,
            format_warning=format_recommendation_warning,
        )

    def _on_recommend_requested(self, strategy_name: str, paths: list[str]) -> None:
        """Adapter: BuildScreen emits (strategy_name, paths), recommend_playlist reads from widgets."""
        self._recommendation_coordinator.on_recommend_requested(strategy_name, paths)

    def _on_copilot_variant_applied(self, index: int) -> None:
        """Adapter: BuildScreen emits variant index, apply method reads from table."""
        if hasattr(self, "_build_screen") and 0 <= index < self._build_screen.copilot_table.rowCount():
            self._build_screen.copilot_table.selectRow(index)
        self.apply_selected_prep_copilot_variant()

    def _on_metadata_export_requested(self, status_filter: str, missing_filter: str) -> None:
        """Route metadata export to the correct exporter based on active filters."""
        # Map display labels back to internal field names
        missing_field = _MISSING_METADATA_FILTERS.get(missing_filter)
        # Normalise status filter: "All" or unknown → None
        norm_status: str | None = (
            status_filter.casefold() if status_filter.casefold() in {"complete", "incomplete"} else None
        )
        self.export_metadata_status_to_serato(status=norm_status, missing_field=missing_field)

    def _on_exclude_requested(self) -> None:
        """Add currently selected library tracks to excluded_paths."""
        new_excluded = self._state.excluded_paths | frozenset(self._library_selected_paths)
        self.excluded_paths = new_excluded
        self._sync_state()

    def _on_lock_requested(self) -> None:
        """Add currently selected library tracks to locked_paths."""
        new_locked = self._state.locked_paths | frozenset(self._library_selected_paths)
        self.locked_paths = new_locked
        self._sync_state()

    def _on_clear_constraints(self) -> None:
        """Reset all excluded and locked constraints."""
        self.excluded_paths = frozenset()
        self.locked_paths = frozenset()
        self._sync_state()

    def _on_library_filters_cleared(self, active_labels: list[str]) -> None:
        """Record a cleared-filters action so it can be undone (R1, spec scope: clear filters)."""
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
        """Navigate to export only if readiness allows it."""
        vm = ReviewViewModel()
        if vm.can_export(self._state):
            self.workflow_tabs.setCurrentIndex(3)

    def _on_track_remove_requested(self, path: str) -> None:
        """Remove a track from the session playlist, recording it as an undoable action."""
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
        """Add *path* to the removed set and re-render the session playlist."""
        self._state.playlist_removed_paths = self._state.playlist_removed_paths | {path}
        self._sync_state()

    def _apply_track_restored(self, path: str) -> None:
        """Remove *path* from the removed set and re-render the session playlist."""
        self._state.playlist_removed_paths = self._state.playlist_removed_paths - {path}
        self._sync_state()

    def _on_track_play_requested(self, path: str) -> None:
        """Open a track in the system default audio player."""
        try:
            subprocess.Popen(["open", path])  # macOS
        except Exception as exc:
            LOGGER.warning("Could not open track %s: %s", path, exc)
            self.status_label.setText(self.tr("Could not open: {0}").format(Path(path).name))

    def _on_preview_play_requested(self, path: str) -> None:
        """Load and play a track preview in the internal audio player."""
        self._audio_player.stop()
        self._audio_player.load(path)

    def _on_live_load_next(self, path: str) -> None:
        """Delegate Live Assistant load-next to the coordinator."""
        self._live_assistant_coordinator.load_next(path)

    def _on_player_state_changed(self, state: object) -> None:
        """Update LibraryScreen highlight when player state changes."""
        from xfinaudio.desktop.audio_player_state import PlayerState

        if state == PlayerState.PLAYING:
            self._library_screen.set_playing_row(self._audio_player._source_path)
        elif state in (PlayerState.IDLE, PlayerState.ERROR):
            self._library_screen.set_playing_row(None)

    def _on_player_error(self, message: str) -> None:
        """Handle audio player errors by clearing the playing row and logging."""
        LOGGER.warning("Audio preview error: %s", message)
        self._library_screen.set_playing_row(None)
        self.status_label.setText(self.tr("Preview error: {0}").format(message))
