"""PySide6 desktop walking skeleton for XfinAudio."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

from PySide6.QtCore import Qt, QThread, Slot
from PySide6.QtGui import QColor
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
from xfinaudio.desktop._workers import BackgroundWorker, ScanWorker
from xfinaudio.desktop.export_coordinator import record_export, write_readiness_sidecars
from xfinaudio.desktop.library_filter import metadata_missing_field_records, metadata_status_records
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
from xfinaudio.desktop.table_populators import populate_library_table, populate_recommendation_table
from xfinaudio.exporting.explainability import PlaylistExplanation, build_playlist_explanation
from xfinaudio.exporting.serato_crate import write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    discover_serato_libraries,
    plan_copilot_variant_serato_playlist_export,
    plan_generated_serato_playlist_export,
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    plan_serato_playlist_export,
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
_COMPACT_LIBRARY_TABLE_MAX_HEIGHT = 190
_COMPACT_LIBRARY_TABLE_MIN_HEIGHT = 132
_COMPACT_RESULTS_TABLE_MIN_HEIGHT = 118
_COMPACT_REVIEW_TABLE_MIN_HEIGHT = 100
_COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT = 72
_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT = 92
_COMPACT_TABLE_ROW_HEIGHT = 24
_SERATO_EXPORT_HISTORY_LIMIT = 5
_TRACK_TITLE_COLUMN = 0
_TRACK_MISSING_COLUMN = 5
_TRACK_STATUS_COLUMN = 8
_TRACK_PATH_COLUMN = 9
_TRACK_TABLE_COLUMN_WIDTHS = (160, 145, 70, 70, 76, 150, 130, 140, 86, 220)
_RECOMMENDATION_TABLE_COLUMN_WIDTHS = (160, 150, 72, 70, 82, 130, 145, 92, 180, 120, 150)
_REVIEW_TABLE_COLUMN_WIDTHS = (70, 170, 170, 100, 100, 112, 100, 110, 180)
_SERATO_EXPORT_HISTORY_COLUMN_WIDTHS = (86, 110, 70, 260, 260, 260)
_DJ_READINESS_TABLE_COLUMN_WIDTHS = (180, 112, 520)
_READINESS_STATUS_COLORS = {"ready": "#1fd16a", "needs_review": "#ffb000", "blocked": "#ff4d4f"}
_READINESS_STATUS_TOOLTIPS = {
    "ready": "Ready: no action needed",
    "needs_review": "Needs Review: inspect before export",
    "blocked": "Blocked: fix before export",
}
_READINESS_STATUS_LABELS = {"ready": "Ready", "needs_review": "Needs Review", "blocked": "Blocked"}

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

_DJ_VISUAL_STYLESHEET = """
QMainWindow {
    background: #0b0f14;
}
QWidget {
    background: #0b0f14;
    color: #edf5ff;
    font-size: 13px;
}
QLabel {
    color: #d7e4f2;
    font-weight: 600;
}
QLabel#statusLabel {
    color: #ffb000;
    padding: 6px 8px;
    border: 1px solid #2d3744;
    border-radius: 8px;
    background: #111923;
}
QLabel#guidanceLabel {
    color: #9fb3c8;
}
QPushButton {
    background: #1c2733;
    color: #edf5ff;
    border: 1px solid #344456;
    border-radius: 8px;
    padding: 5px 10px;
    font-weight: 700;
}
QPushButton:hover {
    background: #253445;
    border-color: #00d4ff;
}
QPushButton:disabled {
    background: #141a21;
    color: #66717d;
    border-color: #202832;
}
QPushButton#primaryAction {
    background: #00d4ff;
    color: #061018;
    border-color: #00d4ff;
}
QPushButton#seratoExportButton {
    background: #ffb000;
    color: #121212;
    border-color: #ffcf5c;
}
QPushButton#primaryAction:disabled,
QPushButton#seratoExportButton:disabled {
    background: #141a21;
    color: #66717d;
    border-color: #202832;
}
QComboBox {
    background: #17212c;
    color: #edf5ff;
    border: 1px solid #344456;
    border-radius: 8px;
    padding: 5px 8px;
}
QLineEdit {
    background: #111923;
    color: #edf5ff;
    border: 1px solid #344456;
    border-radius: 8px;
    padding: 5px 8px;
}
QLineEdit:focus {
    border-color: #00d4ff;
}
QTableWidget {
    background: #101820;
    alternate-background-color: #14202a;
    color: #edf5ff;
    gridline-color: #243241;
    border: 1px solid #263544;
    border-radius: 8px;
    selection-background-color: #005b86;
    selection-color: #ffffff;
}
QHeaderView::section {
    background: #182635;
    color: #00d4ff;
    border: 0;
    border-right: 1px solid #334455;
    padding: 5px 6px;
    font-weight: 800;
}
QTableCornerButton::section {
    background: #182635;
    border: 0;
}
"""


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

        library_page = QWidget()
        library_layout = QVBoxLayout()
        library_layout.addWidget(self.library_decision_label)
        library_layout.addLayout(library_status_controls)
        library_layout.addLayout(library_filter_controls)
        library_layout.addWidget(self.tracks_table, 1)
        library_page.setLayout(library_layout)

        build_page = QWidget()
        build_layout = QVBoxLayout()
        build_layout.addWidget(self.build_decision_label)
        build_layout.addWidget(self.recommendation_guidance_label)
        build_layout.addLayout(recommendation_controls)
        build_layout.addLayout(prep_copilot_controls)
        build_layout.addWidget(self.prep_copilot_table)
        build_layout.addStretch(1)
        build_page.setLayout(build_layout)

        review_page = QWidget()
        review_layout = QVBoxLayout()
        review_layout.addWidget(self.review_decision_label)
        review_layout.addWidget(self.recommendation_table, 2)
        review_layout.addWidget(self.review_summary_label)
        review_layout.addWidget(self.dj_readiness_label)
        review_layout.addWidget(self.dj_readiness_table)
        review_layout.addWidget(self.transition_review_table, 1)
        review_page.setLayout(review_layout)

        export_page = QWidget()
        export_layout = QVBoxLayout()
        export_layout.addWidget(self.export_decision_label)
        export_layout.addWidget(self.applied_copilot_variant_label)
        export_layout.addWidget(self.export_guidance_label)
        export_layout.addWidget(self.serato_export_history_table)
        export_layout.addWidget(self.serato_preview_button)
        export_layout.addWidget(self.serato_export_button)
        export_layout.addWidget(self.dj_readiness_export_button)
        export_layout.addWidget(self.safe_export_folder_button)
        export_layout.addWidget(self.safe_export_folder_label)
        export_layout.addStretch(1)
        export_page.setLayout(export_layout)

        metadata_page = QWidget()
        metadata_layout = QVBoxLayout()
        metadata_layout.addWidget(self.metadata_decision_label)
        metadata_layout.addWidget(
            QLabel(
                "Use the Library filters to isolate incomplete tracks, export a metadata worklist, "
                "complete it in Serato/Mixed In Key, then scan again."
            )
        )
        metadata_layout.addStretch(1)
        metadata_page.setLayout(metadata_layout)

        self.workflow_tabs = QTabWidget()
        self.workflow_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.workflow_tabs.addTab(library_page, "Library")
        self.workflow_tabs.addTab(build_page, "Build Playlist")
        self.workflow_tabs.addTab(review_page, "Review Mix")
        self.workflow_tabs.addTab(export_page, "Export to Serato")
        self.workflow_tabs.addTab(metadata_page, "Metadata Worklist")

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
        self.selected_folder: Path | None = None
        self.scanned_records: list[TrackRecord] = []
        self._records_by_path: dict[str, TrackRecord] = {}
        self.last_recommendation: PlaylistRecommendation | None = None
        self.last_playlist_explanation: PlaylistExplanation | None = None
        self.last_quality_report: RecommendationQualityReport | None = None
        self.last_dj_readiness_report: DjReadinessReport | None = None
        self.last_prep_copilot_plan: PrepCopilotPlan | None = None
        self.applied_prep_copilot_variant_name: str | None = None
        self.current_scan_cancellation_token: ScanCancellationToken | None = None
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self._recommendation_thread: QThread | None = None
        self._recommendation_worker: BackgroundWorker | None = None
        self.serato_export_history: list[dict[str, str]] = []
        self._table_sort_orders: dict[int, Qt.SortOrder] = {}
        self._active_song_search_query = ""
        self._pre_scan_records_by_path: dict[str, TrackRecord] = {}
        self.selected_folder = self.settings.library.last_scan_folder

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
        self._refresh_export_action_state()

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
        self._refresh_export_action_state()

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
            json_path, csv_path = self._write_serato_readiness_sidecars(result.written_path)
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

    def _write_serato_readiness_sidecars(self, crate_path: Path) -> tuple[Path, Path]:
        """Write DJ Readiness JSON/CSV files next to a Serato crate export."""
        if self.last_dj_readiness_report is None:
            raise ValueError("DJ Readiness report is not available for sidecar export")
        return write_readiness_sidecars(self.last_dj_readiness_report, crate_path)

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
        library = (
            SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
            if serato_folder is not None
            else select_serato_library_for_tracks(
                [track.path for track in self.last_recommendation.ordered_tracks],
                discover_serato_libraries(),
            )
        )
        if crate_name is not None:
            plan = plan_serato_playlist_export(crate_name, self.last_recommendation, library)
        elif self.applied_prep_copilot_variant_name is not None:
            plan = plan_copilot_variant_serato_playlist_export(
                self.applied_prep_copilot_variant_name,
                self.last_recommendation,
                library,
                generated_at=generated_at,
            )
        else:
            plan = plan_generated_serato_playlist_export(
                self.last_recommendation,
                library,
                generated_at=generated_at,
            )
        return plan, library

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

    def _refresh_export_action_state(self) -> None:
        """Enable Serato export only when a recommendation exists."""
        self.serato_preview_button.setEnabled(self.last_recommendation is not None)
        self.serato_export_button.setEnabled(self.last_recommendation is not None)
        self.prep_copilot_button.setEnabled(self._selected_track_controls() is not None)
        self.prep_copilot_apply_button.setEnabled(self.last_prep_copilot_plan is not None)
        self.dj_readiness_export_button.setEnabled(
            self.last_dj_readiness_report is not None and self.settings.export.safe_export_folder is not None
        )

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
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "strategy": self.last_recommendation.strategy.name,
            "tracks": str(len(self.last_recommendation.ordered_tracks)),
            "path": str(written_path),
            "readiness_json_path": "" if readiness_json_path is None else str(readiness_json_path),
            "readiness_csv_path": "" if readiness_csv_path is None else str(readiness_csv_path),
        }
        self.serato_export_history = record_export(self.serato_export_history, entry, _SERATO_EXPORT_HISTORY_LIMIT)
        self._render_serato_export_history()

    def _render_serato_export_history(self) -> None:
        """Render recent Serato export receipts without crowding the desktop layout."""
        self.serato_export_history_table.setRowCount(len(self.serato_export_history))
        self.serato_export_history_table.setVisible(bool(self.serato_export_history))
        for row_index, export_receipt in enumerate(self.serato_export_history):
            values = [
                export_receipt["time"],
                export_receipt["strategy"],
                export_receipt["tracks"],
                export_receipt["path"],
                export_receipt.get("readiness_json_path", ""),
                export_receipt.get("readiness_csv_path", ""),
            ]
            sort_values: list[object] = [
                values[0],
                values[1].casefold(),
                int(values[2]),
                values[3].casefold(),
                values[4].casefold(),
                values[5].casefold(),
            ]
            for column_index, value in enumerate(values):
                item = _table_item(value, sort_values[column_index])
                if column_index in {3, 4, 5}:
                    item.setToolTip(value)
                self.serato_export_history_table.setItem(row_index, column_index, item)

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

    def _end_scan_state(self) -> None:
        """Clear scan state after scan completion or cancellation."""
        self.current_scan_cancellation_token = None
        self._refresh_idle_action_state()

    def _start_scan_worker(self, folder: Path, token: ScanCancellationToken) -> None:
        """Start metadata scanning in a worker thread so the UI stays responsive."""
        thread = QThread(self)
        worker = ScanWorker(
            lambda progress_callback: self.workflow_service.scan_folder(
                folder,
                on_progress=progress_callback,
                cancellation_token=token,
            )
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._show_scan_progress)
        worker.finished.connect(self._finish_scan)
        worker.failed.connect(self._fail_scan)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_scan_worker_refs)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

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
        self._scan_thread = None
        self._scan_worker = None

    def _show_scan_progress(self, progress: ScanProgress) -> None:
        """Render scan progress from the workflow service."""
        self.scan_progress_label.setText(
            f"Scan progress: {progress.processed_count}/{progress.total_count} - {progress.current_path}"
        )

    def cancel_scan(self) -> None:
        """Request cooperative cancellation for the current synchronous scan."""
        if self.current_scan_cancellation_token is None:
            return
        self.current_scan_cancellation_token.cancel()
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
        self._set_applied_copilot_variant(variant.name)
        self.show_recommendation(recommendation.ordered_tracks, recommendation.strategy.name, explanation)
        self.review_summary_label.setText(format_quality_summary(quality_report))
        self.dj_readiness_label.setText(format_dj_readiness_summary(variant.readiness))
        self._populate_dj_readiness_table(variant.readiness)
        self.show_transition_review(explanation)
        self.export_guidance_label.setText("Inspect the selected Prep Copilot variant before exporting it to Serato.")
        self.status_label.setText(f"Applied Prep Copilot variant: {variant.name}")
        self._refresh_export_action_state()

    def _set_applied_copilot_variant(self, variant_name: str | None) -> None:
        """Update applied Copilot variant state and export badge."""
        self.applied_prep_copilot_variant_name = variant_name
        if variant_name is None:
            self.applied_copilot_variant_label.setText("Applied Variant: none")
            self.applied_copilot_variant_label.setToolTip("No Prep Copilot variant is currently applied.")
            return
        self.applied_copilot_variant_label.setText(f"Applied Variant: {variant_name}")
        self.applied_copilot_variant_label.setToolTip("This variant will be used for Serato preview/export.")

    def _populate_prep_copilot_table(self, plan: PrepCopilotPlan) -> None:
        """Render Safe/Balanced/Adventurous copilot variants for quick comparison."""
        self.prep_copilot_table.setHidden(False)
        self.prep_copilot_table.setRowCount(len(plan.variants))
        for row_index, variant in enumerate(plan.variants):
            values = [
                variant.name,
                _READINESS_STATUS_LABELS[variant.readiness.status],
                str(len(variant.recommendation.ordered_tracks)),
                "; ".join([*variant.blockers, *variant.warnings]),
            ]
            for column_index, value in enumerate(values):
                item = _table_item(value, value.casefold() if isinstance(value, str) else value)
                if column_index == 1:
                    item.setBackground(QColor(_READINESS_STATUS_COLORS[variant.readiness.status]))
                    item.setForeground(QColor("#061016"))
                    item.setToolTip(variant.readiness.summary)
                self.prep_copilot_table.setItem(row_index, column_index, item)

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
        """Convert selected track rows into DJ sequencing controls."""
        selected_rows = sorted({index.row() for index in self.tracks_table.selectedIndexes()})
        records_by_path = {record.path: record for record in self.scanned_records}
        selected_records: list[TrackRecord] = []
        seen_paths: set[str] = set()
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
        self.recommend_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.status_label.setText(f"Generating recommendation from {candidate_count} candidate track(s)")

    def _end_recommendation_state(self) -> None:
        """Restore valid idle controls after the optimizer finishes."""
        self._refresh_idle_action_state()

    def _start_recommendation_worker(
        self, records: list[TrackRecord], strategy_name: str, controls: DJControls | None = None
    ) -> None:
        """Start recommendation generation in a worker thread."""
        thread = QThread(self)
        worker = BackgroundWorker(lambda: self.workflow_service.recommend(records, strategy_name, controls=controls))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._finish_recommendation)
        worker.failed.connect(self._fail_recommendation)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_recommendation_worker_refs)
        self._recommendation_thread = thread
        self._recommendation_worker = worker
        thread.start()

    @Slot(object)
    def _finish_recommendation(self, result: Any) -> None:
        """Render a completed background recommendation."""
        self._end_recommendation_state()
        self._set_applied_copilot_variant(None)
        self.last_recommendation = result.recommendation
        self.last_playlist_explanation = result.explanation
        self.last_quality_report = result.quality_report
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
        self._refresh_export_action_state()

    @Slot(object)
    def _fail_recommendation(self, error: object) -> None:
        """Recover the UI if background recommendation generation fails."""
        self._end_recommendation_state()
        self.status_label.setText(f"Recommendation failed: {error}")

    @Slot()
    def _clear_recommendation_worker_refs(self) -> None:
        self._recommendation_thread = None
        self._recommendation_worker = None

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
        self.dj_readiness_label.setText(format_dj_readiness_summary(report))
        self._populate_dj_readiness_table(report)
        self._refresh_export_action_state()

    def _populate_dj_readiness_table(self, report: DjReadinessReport) -> None:
        """Render actionable readiness checks in a compact table."""
        self.dj_readiness_table.setRowCount(len(report.checks))
        status_sort = {"blocked": 0, "needs_review": 1, "ready": 2}
        for row_index, check in enumerate(report.checks):
            values = [check.label, _READINESS_STATUS_LABELS[check.status], check.detail]
            sort_values: list[object] = [
                check.label.casefold(),
                status_sort[check.status],
                check.detail.casefold(),
            ]
            for column_index, value in enumerate(values):
                item = _table_item(value, sort_values[column_index])
                if column_index == 1:
                    item.setBackground(QColor(_READINESS_STATUS_COLORS[check.status]))
                    item.setForeground(QColor("#061016"))
                    item.setToolTip(_READINESS_STATUS_TOOLTIPS[check.status])
                self.dj_readiness_table.setItem(row_index, column_index, item)

    def show_transition_review(self, explanation: PlaylistExplanation) -> None:
        """Render transition component scores and warnings in the review table."""
        self.transition_review_table.setRowCount(len(explanation.transitions))
        for row_index, transition in enumerate(explanation.transitions):
            values = [
                str(transition.order),
                _track_review_name(transition.left),
                _track_review_name(transition.right),
                _format_review_score(_component_score(transition, "key_score", "harmonic")),
                _format_review_score(_component_score(transition, "bpm_score", "bpm")),
                _format_review_score(_component_score(transition, "energy_score", "energy")),
                _format_review_score(_component_score(transition, "tag_score", "tags")),
                _format_review_score(transition.final_score),
                "; ".join(format_recommendation_warning(warning) for warning in transition.warnings),
            ]
            sort_values = [
                transition.order,
                values[1].casefold(),
                values[2].casefold(),
                _score_sort_value(_component_score(transition, "key_score", "harmonic")),
                _score_sort_value(_component_score(transition, "bpm_score", "bpm")),
                _score_sort_value(_component_score(transition, "energy_score", "energy")),
                _score_sort_value(_component_score(transition, "tag_score", "tags")),
                _score_sort_value(transition.final_score),
                values[8].casefold(),
            ]
            for column_index, value in enumerate(values):
                self.transition_review_table.setItem(
                    row_index,
                    column_index,
                    _table_item(value, sort_values[column_index]),
                )
