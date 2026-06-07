"""PySide6 desktop walking skeleton for XfinAudio."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService, ScanService, TrackPersistence
from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.export_coordinator import (
    build_serato_export_entry,
    plan_serato_export,
    record_export,
    write_readiness_sidecars,
)
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.library_filter import metadata_missing_field_records, metadata_status_records
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.metadata_view_model import MetadataViewModel
from xfinaudio.desktop.navigation_controller import NavigationController
from xfinaudio.desktop.recommendation_controller import RecommendationController
from xfinaudio.desktop.recommendation_presenter import build_recommendation_pool
from xfinaudio.desktop.rendering import (
    _component_score,
    _format_missing_metadata,
    _format_review_score,
    _format_track_tags,
    _missing_worklist_display_name,
    _score_sort_value,
    _table_item,
    _track_review_name,
    format_quality_summary,
    format_recommendation_warning,
)
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.scan_controller import ScanController
from xfinaudio.desktop.screens import (
    BuildScreen,
    ExportScreen,
    LibraryScreen,
    MetadataScreen,
    ReviewScreen,
)
from xfinaudio.desktop.table_populators import (
    populate_dj_readiness_table,
    populate_library_table,
    populate_prep_copilot_table,
    populate_recommendation_table,
    populate_serato_export_history_table,
    populate_transition_review_table,
)
from xfinaudio.desktop.theme import (
    _COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT,
    _COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT,
    _COMPACT_LIBRARY_TABLE_MAX_HEIGHT,
    _COMPACT_LIBRARY_TABLE_MIN_HEIGHT,
    _COMPACT_RESULTS_TABLE_MIN_HEIGHT,
    _COMPACT_REVIEW_TABLE_MIN_HEIGHT,
    _COMPACT_TABLE_ROW_HEIGHT,
    _DJ_READINESS_TABLE_COLUMN_WIDTHS,
    _DJ_VISUAL_STYLESHEET,
    _READINESS_STATUS_COLORS,
    _READINESS_STATUS_LABELS,
    _READINESS_STATUS_TOOLTIPS,
    _RECOMMENDATION_TABLE_COLUMN_WIDTHS,
    _REVIEW_TABLE_COLUMN_WIDTHS,
    _SERATO_EXPORT_HISTORY_COLUMN_WIDTHS,
    _TRACK_TABLE_COLUMN_WIDTHS,
)
from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.exporting.serato_crate import write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    SeratoLibraryNotFoundError,
    discover_serato_libraries,
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    select_serato_library_for_tracks,
)
from xfinaudio.library.models import MetadataStatus, TrackRecord
from xfinaudio.library.scan_service import MetadataScanService, ScanCancellationToken, ScanProgress
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
from xfinaudio.recommendation.strategies import available_strategies

LOGGER = logging.getLogger(__name__)


class SettingsPersistence(Protocol):
    """Persistence boundary for app settings updates from the desktop UI."""

    def save(self, settings: AppSettings) -> None:
        """Persist application settings."""


_EMPTY_REVIEW_SUMMARY = "No recommendation is ready for review."
_RECOMMENDATION_READY_GUIDANCE = (
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist."
)
_DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT = 25
_SERATO_EXPORT_HISTORY_LIMIT = 5
_SCREEN_NAMES = ["library", "build", "review", "export", "metadata"]
_TRACK_TITLE_COLUMN = 0
_TRACK_MISSING_COLUMN = 5
_TRACK_STATUS_COLUMN = 8
_TRACK_PATH_COLUMN = 9

_MISSING_METADATA_FILTERS = {
    "Missing BPM": "bpm",
    "Missing Key": "camelot_key",
    "Missing Energy": "energy_level",
}

_TRANSITION_REVIEW_HEADERS = [
    "Order",
    "From",
    "To",
    "Key Score",
    "BPM Score",
    "Energy Score",
    "Tag Score",
    "Final Score",
    "Warnings",
]


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
        self._sync_state()

    def closeEvent(self, event: object) -> None:
        """Stop all background threads before the window is destroyed."""
        if self._scan_controller._scan_thread is not None:
            self._scan_controller._scan_thread.quit()
            self._scan_controller._scan_thread.wait(2000)
        if self._recommendation_controller._recommendation_thread is not None:
            self._recommendation_controller._recommendation_thread.quit()
            self._recommendation_controller._recommendation_thread.wait(2000)
        super().closeEvent(event)  # type: ignore[arg-type]

    def _build_layout(self) -> None:
        """Assemble widget layout hierarchy, tab pages, and central window container."""
        controls = QHBoxLayout()
        controls.addWidget(self.folder_button)
        controls.addWidget(self.scan_button)
        controls.addWidget(self.cancel_scan_button)

        library_status_controls = QHBoxLayout()
        library_status_controls.addWidget(self.folder_label)
        library_status_controls.addWidget(self.library_guidance_label, 1)
        library_status_controls.addWidget(self.scan_progress_label)

        library_filter_controls = QHBoxLayout()
        library_filter_controls.addWidget(self.metadata_status_filter_combo)
        library_filter_controls.addWidget(self.missing_metadata_filter_combo)
        library_filter_controls.addWidget(self.song_search_input)
        library_filter_controls.addWidget(self.metadata_status_export_button)
        library_filter_controls.addStretch(1)

        recommendation_controls = QHBoxLayout()
        recommendation_controls.addWidget(QLabel("Strategy"))
        recommendation_controls.addWidget(self.strategy_combo, 1)
        recommendation_controls.addWidget(self.recommend_button)

        prep_copilot_controls = QHBoxLayout()
        prep_copilot_controls.addWidget(QLabel("Set Tracks"))
        prep_copilot_controls.addWidget(self.prep_copilot_target_count_input)
        prep_copilot_controls.addWidget(self.prep_copilot_genre_focus_input)
        prep_copilot_controls.addWidget(self.prep_copilot_button)
        prep_copilot_controls.addWidget(self.prep_copilot_apply_button)
        prep_copilot_controls.addStretch(1)

        self.workflow_tabs = QTabWidget()
        self.workflow_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.workflow_tabs.addTab(self._library_screen, "Library")
        self.workflow_tabs.addTab(self._build_screen, "Build Playlist")
        self.workflow_tabs.addTab(self._review_screen, "Review Mix")
        self.workflow_tabs.addTab(self._export_screen, "Export to Serato")
        self.workflow_tabs.addTab(self._metadata_screen, "Metadata Worklist")

        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addWidget(self.workflow_tabs, 1)
        layout.addWidget(self.status_label)
        self._apply_compact_mac_layout(
            layout,
            controls,
            recommendation_controls,
            library_status_controls,
            library_filter_controls,
            prep_copilot_controls,
        )

        container = QWidget()
        # Reparent all widgets removed from tab-page layouts.
        # Without a parent, Qt shows them as floating top-level windows when
        # setHidden(False) or show() is called. Labels are reparented but kept
        # visible (code still reads their text); interactive widgets are hidden.
        _orphaned_labels = [
            self.review_summary_label,
            self.dj_readiness_label,
            self.build_decision_label,
            self.review_decision_label,
            self.export_decision_label,
            self.recommendation_guidance_label,
            self.export_guidance_label,
            self.applied_copilot_variant_label,
            self.safe_export_folder_label,
        ]
        _orphaned_interactive = [
            self.prep_copilot_table,
            self.recommendation_table,
            self.dj_readiness_table,
            self.transition_review_table,
            self.serato_export_history_table,
            self.serato_preview_button,
            self.serato_export_button,
            self.dj_readiness_export_button,
            self.safe_export_folder_button,
        ]
        for widget in _orphaned_labels:
            widget.setParent(container)
        for widget in _orphaned_interactive:
            widget.setParent(container)
            widget.hide()
        container.setLayout(layout)
        self.setCentralWidget(container)

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
        self._library_vm = LibraryViewModel()
        self._build_vm = BuildViewModel()
        self._review_vm = ReviewViewModel()
        self._export_vm = ExportViewModel()
        self._metadata_vm = MetadataViewModel()
        self._library_screen = LibraryScreen()
        self._build_screen = BuildScreen()
        self._review_screen = ReviewScreen()
        self._export_screen = ExportScreen()
        self._metadata_screen = MetadataScreen()

    def _sync_state(self) -> None:
        """Update transient computed fields in _state, then render all screens."""
        _tab_index = self.workflow_tabs.currentIndex()
        self._state.settings = self.settings
        self._state.is_scanning = self.current_scan_cancellation_token is not None
        self._state.is_recommending = self._is_recommending
        self._state.current_screen = _SCREEN_NAMES[_tab_index] if 0 <= _tab_index < len(_SCREEN_NAMES) else "library"
        self._render_screens()

    def _render_screens(self) -> None:
        """Update all screens with current AppState."""
        self._library_screen.render(self._library_vm, self._state)
        self._build_screen.render(self._build_vm, self._state)
        self._review_screen.render(self._review_vm, self._state)
        self._export_screen.render(self._export_vm, self._state)
        self._metadata_screen.render(self._state, self._metadata_vm)
        self._update_tab_states()

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

    def _update_tab_states(self) -> None:
        """Enable/disable tabs based on NavigationController rules."""
        for index, screen_name in enumerate(_SCREEN_NAMES):
            self.workflow_tabs.setTabEnabled(index, self._nav.can_go_to(screen_name, self._state))

    def _build_widgets(self) -> None:
        """Build constructor widgets and intrinsic widget configuration."""
        self.setWindowTitle("XfinAudio")
        self.folder_button = QPushButton("Choose Folder")
        self.scan_button = QPushButton("Scan Metadata")
        self.scan_button.setEnabled(False)
        self.cancel_scan_button = QPushButton("Cancel Scan")
        self.cancel_scan_button.setEnabled(False)
        self.folder_label = QLabel("Library: none")
        self.library_guidance_label = QLabel("Choose a folder to scan metadata.")
        self.recommendation_guidance_label = QLabel("Scan metadata before recommending a playlist.")
        self.export_guidance_label = QLabel(
            "Review recommendations before exporting; desktop export setup is intentionally out of scope."
        )
        self.applied_copilot_variant_label = QLabel("Applied Variant: none")
        self.applied_copilot_variant_label.setToolTip("No Prep Copilot variant is currently applied.")
        self.safe_export_folder_button = QPushButton("Choose Safe Export Folder")
        self.safe_export_folder_label = QLabel(self._format_safe_export_folder_label())
        self.serato_preview_button = QPushButton("Preview Serato Export")
        self.serato_preview_button.setEnabled(False)
        self.serato_export_button = QPushButton("Export to Serato Crate")
        self.serato_export_button.setEnabled(False)
        self.dj_readiness_export_button = QPushButton("Export DJ Readiness Report")
        self.dj_readiness_export_button.setEnabled(False)
        self.scan_progress_label = QLabel("Scan: idle")
        self.status_label = QLabel("Ready")
        self.library_decision_label = QLabel("DJ Decision Point: choose source, filters, and the track anchor.")
        self.build_decision_label = QLabel("DJ Decision Point: choose strategy, target length, and genre focus.")
        self.review_decision_label = QLabel(
            "DJ Decision Point: accept the mix or revise anchor, metadata, or strategy."
        )
        self.export_decision_label = QLabel("DJ Decision Point: preview crate target before writing to Serato.")
        self.metadata_decision_label = QLabel("DJ Decision Point: complete missing metadata, then refresh the library.")
        self.song_search_input = QLineEdit()
        self.song_search_input.setPlaceholderText("Search songs")
        self.song_search_input.setClearButtonEnabled(True)
        self.song_search_input.setMinimumWidth(160)
        self.song_search_input.setMaximumWidth(220)
        self.metadata_status_filter_combo = QComboBox()
        self.metadata_status_filter_combo.addItems(["All statuses", "Complete", "Incomplete"])
        self.missing_metadata_filter_combo = QComboBox()
        self.missing_metadata_filter_combo.addItems(["All missing fields", *_MISSING_METADATA_FILTERS])
        self.metadata_status_export_button = QPushButton("Export Status Crate")
        self.metadata_status_export_button.setEnabled(False)
        self.tracks_table = QTableWidget(0, 10)
        self.tracks_table.setHorizontalHeaderLabels(
            ["Title", "Artist", "BPM", "Key", "Energy", "Missing", "Genre", "Tags/Subgenre", "Status", "Path"]
        )
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(available_strategies())
        self.recommend_button = QPushButton("Recommend Playlist")
        self.recommend_button.setEnabled(False)
        self.prep_copilot_target_count_input = QSpinBox()
        self.prep_copilot_target_count_input.setRange(2, 100)
        self.prep_copilot_target_count_input.setValue(25)
        self.prep_copilot_genre_focus_input = QLineEdit()
        self.prep_copilot_genre_focus_input.setPlaceholderText("Genre focus")
        self.prep_copilot_genre_focus_input.setMinimumWidth(160)
        self.prep_copilot_genre_focus_input.setMaximumWidth(360)
        self.prep_copilot_button = QPushButton("Generate Prep Copilot")
        self.prep_copilot_button.setEnabled(False)
        self.prep_copilot_apply_button = QPushButton("Apply Selected Variant")
        self.prep_copilot_apply_button.setEnabled(False)
        self.recommendation_table = QTableWidget(0, 11)
        self.recommendation_table.setHorizontalHeaderLabels(
            [
                "Title",
                "Artist",
                "BPM",
                "Key",
                "Energy",
                "Genre",
                "Tags/Subgenre",
                "Strategy",
                "Path",
                "Transition Score",
                "Warnings",
            ]
        )
        self.prep_copilot_table = QTableWidget(0, 4)
        self.prep_copilot_table.setHorizontalHeaderLabels(["Variant", "Readiness", "Tracks", "Warnings"])
        self.prep_copilot_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.prep_copilot_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.review_summary_label = QLabel(_EMPTY_REVIEW_SUMMARY)
        self.dj_readiness_label = QLabel("DJ Readiness: No recommendation ready.")
        self.dj_readiness_table = QTableWidget(0, 3)
        self.dj_readiness_table.setHorizontalHeaderLabels(["Check", "Status", "Detail"])
        self.transition_review_table = QTableWidget(0, len(_TRANSITION_REVIEW_HEADERS))
        self.transition_review_table.setHorizontalHeaderLabels(_TRANSITION_REVIEW_HEADERS)
        self.serato_export_history_table = QTableWidget(0, 6)
        self.serato_export_history_table.setHorizontalHeaderLabels(
            ["Time", "Strategy", "Tracks", "Serato Crate", "Readiness JSON", "Readiness CSV"]
        )
        self.serato_export_history_table.setVisible(False)
        self.folder_label.setWordWrap(False)
        self.folder_label.setMaximumWidth(220)
        self.library_guidance_label.setWordWrap(False)
        self.library_guidance_label.setMaximumWidth(720)
        self.scan_progress_label.setWordWrap(False)
        self.scan_progress_label.setMaximumWidth(140)
        self.recommendation_guidance_label.setWordWrap(True)
        self.export_guidance_label.setWordWrap(True)
        for label in (self.folder_label, self.library_guidance_label, self.scan_progress_label):
            label.setMaximumHeight(24)

    def _connect_widget_signals(self) -> None:
        """Connect constructor-created widgets to their existing slots and sorting handlers."""
        self.folder_button.clicked.connect(self.choose_folder)
        self.scan_button.clicked.connect(self.scan_selected_folder)
        self.cancel_scan_button.clicked.connect(self.cancel_scan)
        self.recommend_button.clicked.connect(self.recommend_playlist)
        self.prep_copilot_button.clicked.connect(self.generate_prep_copilot)
        self.prep_copilot_apply_button.clicked.connect(self.apply_selected_prep_copilot_variant)
        self.prep_copilot_table.itemDoubleClicked.connect(self._apply_prep_copilot_item)
        self.tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)
        self.safe_export_folder_button.clicked.connect(self.choose_safe_export_folder)
        self.serato_preview_button.clicked.connect(lambda: self.preview_serato_export())
        self.serato_export_button.clicked.connect(lambda: self.export_recommendation_to_serato())
        self.dj_readiness_export_button.clicked.connect(lambda: self.export_dj_readiness_report())
        self.song_search_input.textChanged.connect(lambda text: self._apply_song_filter(text, clear_selection=True))
        self.metadata_status_filter_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self.missing_metadata_filter_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self.metadata_status_export_button.clicked.connect(lambda: self.export_metadata_status_to_serato())
        self._scan_controller.scan_progress_updated.connect(self._show_scan_progress)
        self._scan_controller.scan_completed.connect(self._finish_scan)
        self._scan_controller.scan_failed.connect(self._fail_scan)
        self._scan_controller.worker_cleared.connect(self._clear_scan_worker_refs)
        self._recommendation_controller.recommendation_completed.connect(self._finish_recommendation)
        self._recommendation_controller.recommendation_failed.connect(self._fail_recommendation)
        self._recommendation_controller.worker_cleared.connect(self._clear_recommendation_worker_refs)
        # LibraryScreen signals
        self._library_screen.folder_change_requested.connect(self.choose_folder)
        self._library_screen.scan_requested.connect(self.scan_selected_folder)
        self._library_screen.cancel_scan_requested.connect(self.cancel_scan)
        self._library_screen.selection_changed.connect(self._on_library_selection_changed)
        self._library_screen.metadata_screen_requested.connect(
            lambda: self.workflow_tabs.setCurrentIndex(4)
        )
        self._library_screen.proceed_button.clicked.connect(
            lambda: self.workflow_tabs.setCurrentIndex(1)
        )
        # BuildScreen signals
        self._build_screen.recommend_requested.connect(self._on_recommend_requested)
        self._build_screen.copilot_generate_requested.connect(self.generate_prep_copilot)
        self._build_screen.copilot_variant_applied.connect(self._on_copilot_variant_applied)
        self._build_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(0))
        self._build_screen.proceed_button.clicked.connect(
            lambda: self.workflow_tabs.setCurrentIndex(2)
        )
        # ReviewScreen signals
        self._review_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(1))
        self._review_screen.proceed_to_export_requested.connect(self._on_proceed_to_export)
        # ExportScreen signals
        self._export_screen.preview_requested.connect(self.preview_serato_export)
        self._export_screen.export_requested.connect(self.export_recommendation_to_serato)
        self._export_screen.readiness_export_requested.connect(
            lambda: self.export_dj_readiness_report()
        )
        self._export_screen.safe_folder_change_requested.connect(self.choose_safe_export_folder)
        self._export_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(2))
        # MetadataScreen signals
        self._metadata_screen.back_requested.connect(lambda: self.workflow_tabs.setCurrentIndex(0))
        self._metadata_screen.filter_changed.connect(self._sync_state)
        self._metadata_screen.export_requested.connect(self._on_metadata_export_requested)
        for table in (
            self.tracks_table,
            self.recommendation_table,
            self.prep_copilot_table,
            self.transition_review_table,
            self.dj_readiness_table,
            self.serato_export_history_table,
        ):
            self._connect_table_sorting(table)

    def _apply_compact_mac_layout(
        self,
        layout: QVBoxLayout,
        controls: QHBoxLayout,
        recommendation_controls: QHBoxLayout,
        library_status_controls: QHBoxLayout,
        library_filter_controls: QHBoxLayout,
        prep_copilot_controls: QHBoxLayout,
    ) -> None:
        """Use dense desktop spacing so the library browser does not dominate MacBook screens."""
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        controls.setSpacing(8)
        library_status_controls.setSpacing(8)
        library_filter_controls.setSpacing(8)
        recommendation_controls.setSpacing(8)
        prep_copilot_controls.setSpacing(8)

        self.folder_button.setMinimumWidth(220)
        self.scan_button.setMinimumWidth(220)
        self.cancel_scan_button.setMinimumWidth(220)
        self.recommend_button.setMinimumWidth(220)
        self.recommend_button.setMaximumWidth(260)
        self.prep_copilot_button.setMinimumWidth(190)
        self.prep_copilot_button.setMaximumWidth(220)
        self.prep_copilot_apply_button.setMaximumWidth(220)
        self.metadata_status_filter_combo.setMaximumWidth(170)
        self.missing_metadata_filter_combo.setMaximumWidth(220)
        self.metadata_status_export_button.setMaximumWidth(220)

        self.tracks_table.setMinimumHeight(_COMPACT_LIBRARY_TABLE_MIN_HEIGHT)
        self.tracks_table.setMaximumHeight(_COMPACT_LIBRARY_TABLE_MAX_HEIGHT)
        self.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.prep_copilot_table.setMaximumHeight(_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT)
        self.prep_copilot_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.prep_copilot_table.setHidden(True)
        self.recommendation_table.setMinimumHeight(_COMPACT_RESULTS_TABLE_MIN_HEIGHT)
        self.recommendation_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.transition_review_table.setMinimumHeight(_COMPACT_REVIEW_TABLE_MIN_HEIGHT)
        self.transition_review_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.dj_readiness_table.setMaximumHeight(_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT)
        self.dj_readiness_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.serato_export_history_table.setMaximumHeight(_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT)
        self.serato_export_history_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_compact_table_columns()
        self._set_recommendation_sections_expanded(False)

    def _apply_compact_table_columns(self) -> None:
        """Allocate readable column widths while letting path/warning columns absorb spare space."""
        table_widths = (
            (self.tracks_table, _TRACK_TABLE_COLUMN_WIDTHS),
            (self.recommendation_table, _RECOMMENDATION_TABLE_COLUMN_WIDTHS),
            (self.prep_copilot_table, (120, 120, 80, 420)),
            (self.transition_review_table, _REVIEW_TABLE_COLUMN_WIDTHS),
            (self.dj_readiness_table, _DJ_READINESS_TABLE_COLUMN_WIDTHS),
            (self.serato_export_history_table, _SERATO_EXPORT_HISTORY_COLUMN_WIDTHS),
        )
        for table, widths in table_widths:
            for column_index, width in enumerate(widths):
                table.setColumnWidth(column_index, width)
            table.horizontalHeader().setStretchLastSection(True)

    def _apply_visual_design(self) -> None:
        """Apply a DJ-focused dark visual theme with clear action hierarchy."""
        self.recommend_button.setObjectName("primaryAction")
        self.serato_export_button.setObjectName("seratoExportButton")
        self.song_search_input.setObjectName("songSearch")
        self.status_label.setObjectName("statusLabel")
        for label in (
            self.folder_label,
            self.library_guidance_label,
            self.scan_progress_label,
            self.recommendation_guidance_label,
            self.export_guidance_label,
            self.safe_export_folder_label,
            self.library_decision_label,
            self.build_decision_label,
            self.review_decision_label,
            self.export_decision_label,
            self.metadata_decision_label,
        ):
            label.setObjectName("guidanceLabel")
        for table in (
            self.tracks_table,
            self.recommendation_table,
            self.prep_copilot_table,
            self.transition_review_table,
            self.dj_readiness_table,
            self.serato_export_history_table,
        ):
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.setWordWrap(False)
            table.verticalHeader().setDefaultSectionSize(_COMPACT_TABLE_ROW_HEIGHT)
            table.verticalHeader().setMinimumSectionSize(_COMPACT_TABLE_ROW_HEIGHT)
            table.verticalHeader().setVisible(False)
        self.setStyleSheet(_DJ_VISUAL_STYLESHEET)

    def _set_recommendation_sections_expanded(self, expanded: bool) -> None:
        """Give vertical space back to browsing until a recommendation exists."""
        maximum_height = 16777215 if expanded else _COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT
        self.recommendation_table.setHidden(not expanded)
        self.transition_review_table.setHidden(not expanded)
        self.dj_readiness_table.setHidden(not expanded)
        self.recommendation_table.setMaximumHeight(maximum_height)
        self.transition_review_table.setMaximumHeight(maximum_height)
        self.dj_readiness_table.setMaximumHeight(
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
        if table is self.tracks_table:
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
            return "No safe export folder selected"
        return f"Safe export folder: {folder}"

    def choose_folder(self) -> None:
        """Open a folder picker and store the selected library folder."""
        folder = QFileDialog.getExistingDirectory(self, "Choose music folder")
        if folder:
            self.set_selected_folder(Path(folder))

    def set_selected_folder(self, folder: Path) -> None:
        """Set the current folder and update the display label."""
        self.selected_folder = folder
        self._persist_last_scan_folder(folder)
        self._clear_scan_dependent_state()
        self.folder_label.setText(str(folder))
        self.library_guidance_label.setText("Folder selected. Scan metadata to find complete Mixed In Key tracks.")
        self.recommendation_guidance_label.setText("Scan metadata before recommending a playlist.")
        self._refresh_idle_action_state()
        self.status_label.setText("Folder selected")
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
            self.tracks_table,
            records,
            item_factory=_table_item,
            format_missing_metadata=_format_missing_metadata,
            format_track_tags=_format_track_tags,
        )
        self._apply_song_filter(clear_selection=False)

    def _apply_song_filter(self, query: str | None = None, *, clear_selection: bool = False) -> None:
        """Hide library rows whose song title/status does not match active browse filters."""
        search_query = (self.song_search_input.text() if query is None else query).strip().casefold()
        if clear_selection and search_query != self._active_song_search_query:
            self.tracks_table.clearSelection()
        self._active_song_search_query = search_query
        status_filter = self._selected_metadata_status_filter()
        missing_filter = self._selected_missing_metadata_filter()
        for row_index in range(self.tracks_table.rowCount()):
            title_item = self.tracks_table.item(row_index, _TRACK_TITLE_COLUMN)
            title = "" if title_item is None else title_item.text().casefold()
            status_item = self.tracks_table.item(row_index, _TRACK_STATUS_COLUMN)
            status = "" if status_item is None else status_item.text()
            path_item = self.tracks_table.item(row_index, _TRACK_PATH_COLUMN)
            path = "" if path_item is None else path_item.text()
            record = self._records_by_path.get(path)
            title_mismatch = bool(search_query) and search_query not in title
            status_mismatch = status_filter is not None and status != status_filter
            missing_mismatch = missing_filter is not None and (
                record is None or missing_filter not in record.missing_required_fields
            )
            self.tracks_table.setRowHidden(row_index, title_mismatch or status_mismatch or missing_mismatch)
        self._refresh_idle_action_state()

    def _selected_metadata_status_filter(self) -> str | None:
        """Return the active complete/incomplete filter, or None for all statuses."""
        status_text = self.metadata_status_filter_combo.currentText().casefold()
        return status_text if status_text in {"complete", "incomplete"} else None

    def _selected_missing_metadata_filter(self) -> str | None:
        """Return the active missing-field audit filter, or None for all missing fields."""
        return _MISSING_METADATA_FILTERS.get(self.missing_metadata_filter_combo.currentText())

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
            self.folder_label.setText("Library: saved")
            self.folder_label.setToolTip("Saved library loaded; no scan folder selected.")
            self.library_guidance_label.setText("Use filters/search, select a complete track, then recommend.")
            self.library_guidance_label.setToolTip(
                "Showing saved library from the app database. Choose a folder to re-scan or update metadata."
            )
        else:
            self.folder_label.setText("Library: saved folder")
            self.folder_label.setToolTip(f"Saved library loaded: {self.selected_folder}")
            self.library_guidance_label.setText("Use filters/search, select a complete track, then recommend.")
            self.library_guidance_label.setToolTip(
                "Saved library loaded. Click Scan Metadata to refresh metadata from the last folder."
            )
        self.recommendation_guidance_label.setText(_RECOMMENDATION_READY_GUIDANCE)
        self.status_label.setText(f"Loaded saved library: {complete_count} complete, {incomplete_count} incomplete")
        self._refresh_idle_action_state()
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
        self.tracks_table.setRowCount(0)
        self.song_search_input.clear()
        self.recommendation_table.setRowCount(0)
        self._set_recommendation_sections_expanded(False)
        self.clear_recommendation_review()
        self.export_guidance_label.setText(
            "Review recommendations before exporting. Serato export is enabled only after a recommendation is ready."
        )

        self._sync_state()

    def _refresh_idle_action_state(self) -> None:
        """Enable only the actions that are valid for the current idle UI state."""
        self.scan_button.setEnabled(self.selected_folder is not None)
        self.recommend_button.setEnabled(self._selected_track_controls() is not None)
        status_filter = self._selected_metadata_status_filter()
        missing_filter = self._selected_missing_metadata_filter()
        self.metadata_status_export_button.setEnabled(
            (missing_filter is not None and bool(self._metadata_missing_field_records(missing_filter)))
            or (status_filter is not None and bool(self._metadata_status_records(status_filter)))
        )
        self.cancel_scan_button.setEnabled(False)

    def choose_safe_export_folder(self) -> None:
        """Open a folder picker and store the selected safe export folder."""
        folder = QFileDialog.getExistingDirectory(self, "Choose safe export folder")
        if folder:
            self.set_safe_export_folder(Path(folder))

    def set_safe_export_folder(self, folder: Path) -> None:
        """Persist a safe export folder if it is not the selected audio folder."""
        if self.selected_folder is not None and folder == self.selected_folder:
            self.status_label.setText("Safe export folder must be outside the selected audio folder")
            return

        self.settings = self.settings.model_copy(update={"export": ExportSettings(safe_export_folder=folder)})
        if self.settings_repository is not None:
            self.settings_repository.save(self.settings)
        self.safe_export_folder_label.setText(self._format_safe_export_folder_label())
        self.status_label.setText("Safe export folder selected")

        self._sync_state()

    def export_dj_readiness_report(self, *, generated_at: datetime | None = None) -> None:
        """Export the latest DJ readiness report as JSON and CSV audit artifacts."""
        if self.last_dj_readiness_report is None:
            self.status_label.setText("Generate a recommendation before exporting DJ readiness")
            return
        safe_folder = self.settings.export.safe_export_folder
        if safe_folder is None:
            self.status_label.setText("Choose a safe export folder before exporting DJ readiness")
            return
        generated_at = generated_at or datetime.now()
        timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
        json_path = safe_folder / f"xfinaudio-dj-readiness-{timestamp}.json"
        csv_path = safe_folder / f"xfinaudio-dj-readiness-{timestamp}.csv"
        json_path, csv_path = write_dj_readiness_report(self.last_dj_readiness_report, json_path, csv_path)
        self.status_label.setText(f"Exported DJ readiness report: {json_path} and {csv_path}")

    def preview_serato_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Preview the Serato crate destination without writing files."""
        if self.last_recommendation is None:
            self.status_label.setText("Generate a recommendation before previewing Serato export")
            return

        try:
            plan, _library = self._plan_current_serato_export(
                serato_folder=serato_folder,
                crate_name=crate_name,
                generated_at=generated_at,
            )
        except SeratoLibraryNotFoundError:
            self.status_label.setText(
                "Serato not found — open Serato DJ Pro at least once to create its library folder"
            )
            return
        except Exception as exc:
            LOGGER.exception("Serato export preview failed")
            self.status_label.setText(f"Serato export preview failed: {exc}")
            return

        variant = self.applied_prep_copilot_variant_name or "none"
        readiness = (
            _READINESS_STATUS_LABELS[self.last_dj_readiness_report.status]
            if self.last_dj_readiness_report is not None
            else "Not available"
        )
        will_write = "yes" if not plan.target_path.exists() else "replace with backup"
        self.export_guidance_label.setText(
            f"Serato export preview: {plan.target_path} | "
            f"Variant: {variant} | Tracks: {len(plan.relative_paths)} | "
            f"Will write: {will_write} | Readiness: {readiness}"
        )
        self.status_label.setText(f"Serato export preview: {plan.target_path}")

    def export_recommendation_to_serato(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> None:
        """Export the current recommendation as a confirmed Serato crate."""
        if self.last_recommendation is None:
            self.status_label.setText("Generate a recommendation before exporting to Serato")
            return

        try:
            plan, library = self._plan_current_serato_export(
                serato_folder=serato_folder,
                crate_name=crate_name,
                generated_at=generated_at,
            )
            result = write_serato_crate(plan, confirm=True)
        except SeratoLibraryNotFoundError:
            self.status_label.setText(
                "Serato not found — open Serato DJ Pro at least once to create its library folder"
            )
            return
        except Exception as exc:
            LOGGER.exception("Serato export failed")
            self.status_label.setText(f"Serato export failed: {exc}")
            return

        backup_note = (
            f" Backup: {result.backup_path}" if result.backup_path is not None else " No previous crate existed."
        )
        readiness_note = ""
        readiness_paths: tuple[Path | None, Path | None] = (None, None)
        if self.last_quality_report is not None:
            self._show_dj_readiness(
                self.last_recommendation,
                self.last_quality_report,
                serato_plan=plan,
                serato_volume_root=library.volume_root,
            )
        if self.last_dj_readiness_report is not None:
            safe_folder = self.settings.export.safe_export_folder
            json_path, csv_path = write_readiness_sidecars(
                self.last_dj_readiness_report, result.written_path, safe_folder=safe_folder
            )
            readiness_paths = (json_path, csv_path)
            readiness_note = f" Readiness reports: {json_path} and {csv_path}."
        self.export_guidance_label.setText(
            f"Serato crate exported: {result.written_path}. "
            "Open Serato DJ Pro and check the crate under Subcrates." + backup_note + readiness_note
        )
        self.status_label.setText(f"Exported Serato crate: {result.written_path}")
        self._record_serato_export(
            result.written_path, readiness_json_path=readiness_paths[0], readiness_csv_path=readiness_paths[1]
        )

    def _plan_current_serato_export(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
        generated_at: datetime | None = None,
    ) -> tuple[Any, SeratoLibrary]:
        """Build the current Serato export plan without writing it."""
        if self.last_recommendation is None:
            raise ValueError("Generate a recommendation before planning Serato export")
        return plan_serato_export(
            self.last_recommendation,
            self.applied_prep_copilot_variant_name,
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
        """Export complete or incomplete metadata worklists as Serato crates."""
        selected_missing_field = missing_field or self._selected_missing_metadata_filter()
        selected_status = status or self._selected_metadata_status_filter()
        if selected_missing_field is not None:
            self._export_missing_metadata_worklist_to_serato(selected_missing_field, serato_folder=serato_folder)
            return

        if selected_status not in {"complete", "incomplete"}:
            self.status_label.setText("Choose Complete or Incomplete before exporting a metadata worklist")
            return

        records = self._metadata_status_records(selected_status)
        if not records:
            self.status_label.setText(f"No {selected_status} tracks are available for metadata export")
            return

        try:
            library = (
                SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
                if serato_folder is not None
                else select_serato_library_for_tracks(
                    [record.path for record in records],
                    discover_serato_libraries(),
                )
            )
            plan = plan_metadata_status_serato_export(records, cast(MetadataStatus, selected_status), library)
            result = write_serato_crate(plan, confirm=True)
        except Exception as exc:
            LOGGER.exception("Serato metadata status export failed")
            self.status_label.setText(f"Serato metadata export failed: {exc}")
            return

        self.export_guidance_label.setText(
            f"Metadata worklist exported: {result.written_path}. "
            "Complete missing metadata in Serato, then choose the same folder and click Scan Metadata "
            "to refresh XfinAudio."
        )
        self.status_label.setText(f"Exported {selected_status} metadata crate: {result.written_path}")

    def _export_missing_metadata_worklist_to_serato(
        self,
        missing_field: str,
        *,
        serato_folder: Path | None = None,
    ) -> None:
        """Export a specific missing-field metadata worklist as a Serato crate."""
        records = self._metadata_missing_field_records(missing_field)
        display_field = _missing_worklist_display_name(missing_field)
        if not records:
            self.status_label.setText(f"No tracks are missing {display_field} for metadata export")
            return

        try:
            library = (
                SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
                if serato_folder is not None
                else select_serato_library_for_tracks(
                    [record.path for record in records],
                    discover_serato_libraries(),
                )
            )
            plan = plan_metadata_missing_field_serato_export(records, missing_field, library)
            result = write_serato_crate(plan, confirm=True)
        except Exception as exc:
            LOGGER.exception("Serato missing-metadata export failed")
            self.status_label.setText(f"Serato metadata export failed: {exc}")
            return

        self.export_guidance_label.setText(
            f"Metadata worklist exported: {result.written_path}. "
            "Complete missing metadata in Serato, then click Scan Metadata in XfinAudio to refresh."
        )
        self.status_label.setText(f"Exported Missing {display_field} metadata crate: {result.written_path}")

    def _record_serato_export(
        self,
        written_path: Path,
        *,
        readiness_json_path: Path | None = None,
        readiness_csv_path: Path | None = None,
    ) -> None:
        """Record a bounded in-session Serato export receipt for user verification."""
        if self.last_recommendation is None:
            return
        entry = build_serato_export_entry(
            self.last_recommendation,
            written_path,
            readiness_json_path=readiness_json_path,
            readiness_csv_path=readiness_csv_path,
        )
        self.serato_export_history = record_export(self.serato_export_history, entry, _SERATO_EXPORT_HISTORY_LIMIT)
        self._sync_state()
        self._render_serato_export_history()

    def _render_serato_export_history(self) -> None:
        """Render recent Serato export receipts without crowding the desktop layout."""
        self.serato_export_history_table.setVisible(bool(self.serato_export_history))
        populate_serato_export_history_table(
            self.serato_export_history_table,
            self.serato_export_history,
            item_factory=_table_item,
        )

    def scan_selected_folder(self) -> None:
        """Scan the selected folder, persist records, and refresh table/status widgets."""
        if self.selected_folder is None:
            self.status_label.setText("Choose a folder before scanning")
            self.library_guidance_label.setText("Choose a Mixed In Key processed folder before scanning metadata.")
            return
        self._pre_scan_records_by_path = {record.path: record for record in self.scanned_records}
        self._begin_scan_state()
        token = self.current_scan_cancellation_token
        folder = self.selected_folder
        if token is None or folder is None:  # pragma: no cover - guarded by _begin_scan_state and folder check
            raise RuntimeError("Scan state was not initialized before starting the scan worker")
        self._start_scan_worker(folder, token)

    def _begin_scan_state(self) -> None:
        """Prepare synchronous scan state and enable cooperative cancellation."""
        self.current_scan_cancellation_token = ScanCancellationToken()
        self.scan_button.setEnabled(False)
        self.recommend_button.setEnabled(False)
        self.cancel_scan_button.setEnabled(True)
        self.scan_progress_label.setText("Scan progress: starting")
        self.status_label.setText("Scanning metadata")
        self._sync_state()

    def _end_scan_state(self) -> None:
        """Clear scan state after scan completion or cancellation."""
        self.current_scan_cancellation_token = None
        self._refresh_idle_action_state()
        self._sync_state()

    def _start_scan_worker(self, folder: Path, token: ScanCancellationToken) -> None:
        """Delegate thread/worker construction to the scan controller."""
        self._scan_controller.start_scan(folder, token)

    @Slot(object)
    def _finish_scan(self, result: Any) -> None:
        """Render a completed background scan result."""
        if result.cancelled:
            self._clear_scan_dependent_state()
            self._end_scan_state()
            self.status_label.setText("Scan canceled; no partial results were saved")
            self.recommendation_guidance_label.setText("Scan metadata before recommending a playlist.")
            return
        self.scanned_records = result.records
        self._sync_state()
        self.show_tracks(result.records, result.complete_count, result.incomplete_count)
        self._end_scan_state()
        self._show_scan_completion_status(result.records)
        self.recommendation_guidance_label.setText(
            _RECOMMENDATION_READY_GUIDANCE
            if self.scanned_records
            else "No tracks found. Choose another folder or re-scan after adding supported audio files."
        )

    def _show_scan_completion_status(self, records: list[TrackRecord]) -> None:
        """Show either first-scan counts or refresh delta compared with the previous visible library."""
        if not self._pre_scan_records_by_path:
            return
        before_records = list(self._pre_scan_records_by_path.values())
        before_incomplete = sum(1 for record in before_records if record.metadata_status == "incomplete")
        after_incomplete = sum(1 for record in records if record.metadata_status == "incomplete")
        fixed_count = sum(
            1
            for record in records
            if record.metadata_status == "complete"
            and self._pre_scan_records_by_path.get(record.path) is not None
            and self._pre_scan_records_by_path[record.path].metadata_status == "incomplete"
        )
        self.status_label.setText(
            f"Refresh complete: {before_incomplete} incomplete → {after_incomplete} incomplete; {fixed_count} fixed"
        )
        self._pre_scan_records_by_path = {}

    @Slot(object)
    def _fail_scan(self, error: object) -> None:
        """Recover the UI if a background scan fails."""
        self._end_scan_state()
        self.status_label.setText(f"Scan failed: {error}")

    @Slot()
    def _clear_scan_worker_refs(self) -> None:
        pass  # Thread/worker refs are now owned and cleared by ScanController.

    def _on_library_selection_changed(self, paths: list[str]) -> None:
        """Update state when user selection changes in LibraryScreen."""
        self._library_selected_paths = paths
        self._refresh_idle_action_state()

    def _show_scan_progress(self, progress: ScanProgress) -> None:
        """Render scan progress from the workflow service."""
        self.scan_progress_label.setText(
            f"Scan progress: {progress.processed_count}/{progress.total_count} - {progress.current_path}"
        )

    def cancel_scan(self) -> None:
        """Request cooperative cancellation for the current synchronous scan."""
        if self.current_scan_cancellation_token is None:
            return
        self._scan_controller.cancel(self.current_scan_cancellation_token)
        self.cancel_scan_button.setEnabled(False)
        self.status_label.setText("Cancel requested; waiting for current file to finish")

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
        self.status_label.setText(f"Scan complete: {complete_count} complete, {incomplete_count} incomplete")

    def generate_prep_copilot(self) -> None:
        """Generate comparable DJ Prep Copilot variants from current selection and intent controls."""
        controls = self._selected_track_controls()
        if controls is None:
            self.last_prep_copilot_plan = None
            self.prep_copilot_table.setRowCount(0)
            self.prep_copilot_apply_button.setEnabled(False)
            self.status_label.setText("Select at least one complete track before generating Prep Copilot")
            return
        records = self._desktop_recommendation_records(controls)
        genre_focus = self.prep_copilot_genre_focus_input.text().strip() or None
        intent = DJSetIntent(
            name="Desktop Prep Copilot",
            strategy=self.strategy_combo.currentText(),
            target_track_count=self.prep_copilot_target_count_input.value(),
            start_path=controls.start_path,
            required_paths=controls.manual_order_paths,
            genre_focus=genre_focus,
        )
        plan = build_prep_copilot_plan(records, intent)
        self.last_prep_copilot_plan = plan
        self._populate_prep_copilot_table(plan)
        self.prep_copilot_apply_button.setEnabled(True)
        self.status_label.setText(f"Generated {len(plan.variants)} Prep Copilot variant(s)")
        self._sync_state()

    def _apply_prep_copilot_item(self, item: QTableWidgetItem) -> None:
        """Apply the Prep Copilot variant represented by a double-clicked table item."""
        self.prep_copilot_table.selectRow(item.row())
        self.apply_selected_prep_copilot_variant()

    def apply_selected_prep_copilot_variant(self) -> None:
        """Apply the selected Prep Copilot variant to the main review/export flow."""
        if self.last_prep_copilot_plan is None:
            self.status_label.setText("Generate and select a Prep Copilot variant before applying")
            return
        selected_rows = sorted({index.row() for index in self.prep_copilot_table.selectedIndexes()})
        if not selected_rows:
            self.status_label.setText("Generate and select a Prep Copilot variant before applying")
            return
        row_index = selected_rows[0]
        if row_index >= len(self.last_prep_copilot_plan.variants):
            self.status_label.setText("Generate and select a Prep Copilot variant before applying")
            return
        variant = self.last_prep_copilot_plan.variants[row_index]
        recommendation = variant.recommendation
        explanation = build_playlist_explanation(recommendation)
        quality_report = build_quality_report(recommendation)
        self.last_recommendation = recommendation
        self.last_playlist_explanation = explanation
        self.last_quality_report = quality_report
        self.last_dj_readiness_report = variant.readiness
        self._sync_state()
        self._set_applied_copilot_variant(variant.name)
        self.show_recommendation(recommendation.ordered_tracks, recommendation.strategy.name, explanation)
        self.review_summary_label.setText(format_quality_summary(quality_report))
        self.dj_readiness_label.setText(format_dj_readiness_summary(variant.readiness))
        self._populate_dj_readiness_table(variant.readiness)
        self.show_transition_review(explanation)
        self.export_guidance_label.setText("Inspect the selected Prep Copilot variant before exporting it to Serato.")
        self.status_label.setText(f"Applied Prep Copilot variant: {variant.name}")


    def _set_applied_copilot_variant(self, variant_name: str | None) -> None:
        """Update applied Copilot variant state and export badge."""
        self.applied_prep_copilot_variant_name = variant_name
        self._sync_state()
        if variant_name is None:
            self.applied_copilot_variant_label.setText("Applied Variant: none")
            self.applied_copilot_variant_label.setToolTip("No Prep Copilot variant is currently applied.")
            return
        self.applied_copilot_variant_label.setText(f"Applied Variant: {variant_name}")
        self.applied_copilot_variant_label.setToolTip("This variant will be used for Serato preview/export.")

    def _populate_prep_copilot_table(self, plan: PrepCopilotPlan) -> None:
        """Render Safe/Balanced/Adventurous copilot variants for quick comparison."""
        self.prep_copilot_table.setHidden(False)
        populate_prep_copilot_table(
            self.prep_copilot_table,
            plan,
            item_factory=_table_item,
            readiness_status_labels=_READINESS_STATUS_LABELS,
            readiness_status_colors=_READINESS_STATUS_COLORS,
        )

    def recommend_playlist(self) -> None:
        """Generate and display a playlist recommendation from scanned records."""
        if not self.scanned_records:
            self.clear_recommendation_review()
            self.status_label.setText("Scan tracks before recommending")
            self.recommendation_guidance_label.setText("Scan metadata before recommending a playlist.")
            return
        strategy_name = self.strategy_combo.currentText()
        controls = self._selected_track_controls()
        if controls is None:
            self.clear_recommendation_review()
            self.recommendation_table.setRowCount(0)
            self._set_recommendation_sections_expanded(False)
            self.status_label.setText("Select at least one complete track before recommending")
            return
        records = self._desktop_recommendation_records(controls)
        self._begin_recommendation_state(len(records))
        self._start_recommendation_worker(records, strategy_name, controls)

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
                    return DJControls(start_path=selected_records[0].path)
                return DJControls(manual_order_paths=[r.path for r in selected_records])

        # Fallback: legacy widget used by automated tests
        selected_rows = sorted({index.row() for index in self.tracks_table.selectedIndexes()})
        selected_records = []
        seen_paths = set()
        for row in selected_rows:
            if self.tracks_table.isRowHidden(row):
                continue
            path_item = self.tracks_table.item(row, _TRACK_PATH_COLUMN)
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
            return DJControls(start_path=selected_records[0].path)
        return DJControls(manual_order_paths=[record.path for record in selected_records])

    def _desktop_recommendation_records(self, controls: DJControls | None) -> list[TrackRecord]:
        """Return an interactive-size recommendation pool while preserving selected control tracks."""
        return build_recommendation_pool(self.scanned_records, controls, _DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT)

    def _begin_recommendation_state(self, candidate_count: int) -> None:
        """Disable recommendation controls while the optimizer runs."""
        self._is_recommending = True
        self.recommend_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.status_label.setText(f"Generating recommendation from {candidate_count} candidate track(s)")
        self._sync_state()

    def _end_recommendation_state(self) -> None:
        """Restore valid idle controls after the optimizer finishes."""
        self._is_recommending = False
        self._refresh_idle_action_state()
        self._sync_state()

    def _start_recommendation_worker(
        self, records: list[TrackRecord], strategy_name: str, controls: DJControls | None = None
    ) -> None:
        """Delegate recommendation thread lifecycle to RecommendationController."""
        self._recommendation_controller.workflow_service = self.workflow_service
        self._recommendation_controller.start_recommendation(records, strategy_name, controls)

    @Slot(object)
    def _finish_recommendation(self, result: Any) -> None:
        """Render a completed background recommendation."""
        self._end_recommendation_state()
        self._set_applied_copilot_variant(None)
        self.last_recommendation = result.recommendation
        self.last_playlist_explanation = result.explanation
        self.last_quality_report = result.quality_report
        self._sync_state()
        self.show_recommendation(
            result.recommendation.ordered_tracks,
            result.recommendation.strategy.name,
            result.explanation,
        )
        self.review_summary_label.setText(format_quality_summary(result.quality_report))
        self._show_dj_readiness(result.recommendation, result.quality_report)
        self.show_transition_review(result.explanation)
        recommended_count = len(result.recommendation.ordered_tracks)
        strategy_name = result.recommendation.strategy.name
        self.status_label.setText(f"Recommended {recommended_count} track(s) using {strategy_name}")
        self.export_guidance_label.setText(
            "Inspect the review table before exporting. Review scores and warnings before any safe export to Serato."
        )


    @Slot(object)
    def _fail_recommendation(self, error: object) -> None:
        """Recover the UI if background recommendation generation fails."""
        self._end_recommendation_state()
        self.status_label.setText(f"Recommendation failed: {error}")

    @Slot()
    def _clear_recommendation_worker_refs(self) -> None:
        pass  # refs owned and cleared by RecommendationController

    def show_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        explanation: PlaylistExplanation | None = None,
    ) -> None:
        """Render recommended records in the playlist table."""
        self._set_recommendation_sections_expanded(bool(records))
        populate_recommendation_table(
            self.recommendation_table,
            records,
            strategy_name,
            explanation,
            item_factory=_table_item,
            format_track_tags=_format_track_tags,
            format_warning=format_recommendation_warning,
        )

    def clear_recommendation_review(self) -> None:
        """Reset recommendation review widgets to their empty state."""
        self.review_summary_label.setText(_EMPTY_REVIEW_SUMMARY)
        self.dj_readiness_label.setText("DJ Readiness: No recommendation ready.")
        self.dj_readiness_table.setRowCount(0)
        self.transition_review_table.setRowCount(0)
        self.prep_copilot_table.setHidden(True)
        if self.recommendation_table.rowCount() == 0:
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
        self.dj_readiness_label.setText(format_dj_readiness_summary(report))
        self._populate_dj_readiness_table(report)


    def _populate_dj_readiness_table(self, report: DjReadinessReport) -> None:
        """Render actionable readiness checks in a compact table."""
        populate_dj_readiness_table(
            self.dj_readiness_table,
            report,
            item_factory=_table_item,
            readiness_status_labels=_READINESS_STATUS_LABELS,
            readiness_status_colors=_READINESS_STATUS_COLORS,
            readiness_status_tooltips=_READINESS_STATUS_TOOLTIPS,
        )

    def show_transition_review(self, explanation: PlaylistExplanation) -> None:
        """Render transition component scores and warnings in the review table."""
        populate_transition_review_table(
            self.transition_review_table,
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
        combo_idx = self.strategy_combo.findText(strategy_name)
        if combo_idx >= 0:
            self.strategy_combo.setCurrentIndex(combo_idx)
        self.recommend_playlist()

    def _on_copilot_variant_applied(self, index: int) -> None:
        """Adapter: BuildScreen emits variant index, apply method reads from table."""
        if hasattr(self, "prep_copilot_table") and 0 <= index < self.prep_copilot_table.rowCount():
            self.prep_copilot_table.selectRow(index)
        self.apply_selected_prep_copilot_variant()

    def _on_metadata_export_requested(self, status_filter: str, missing_filter: str) -> None:
        """Route metadata export to the correct exporter based on active filters."""
        # Map display labels back to internal field names
        missing_field = _MISSING_METADATA_FILTERS.get(missing_filter)
        # Normalise status filter: "All" or unknown → None
        norm_status: str | None = status_filter.casefold() if status_filter.casefold() in {"complete", "incomplete"} else None
        self.export_metadata_status_to_serato(status=norm_status, missing_field=missing_field)

    def _on_proceed_to_export(self) -> None:
        """Navigate to export only if readiness allows it."""
        vm = ReviewViewModel()
        if vm.can_export(self._state):
            self.workflow_tabs.setCurrentIndex(3)
