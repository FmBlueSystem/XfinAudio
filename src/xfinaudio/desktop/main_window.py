"""PySide6 desktop walking skeleton for XfinAudio."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService, ScanService, TrackPersistence
from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.exporting.serato_crate import write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import (
    SeratoLibrary,
    discover_serato_libraries,
    plan_generated_serato_playlist_export,
    plan_metadata_missing_field_serato_export,
    plan_metadata_status_serato_export,
    plan_serato_playlist_export,
    select_serato_library_for_tracks,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import MetadataScanService, ScanCancellationToken, ScanProgress
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.quality.dj_readiness import (
    DjReadinessReport,
    build_dj_readiness_report,
    format_dj_readiness_summary,
)
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import available_strategies


class SettingsPersistence(Protocol):
    """Persistence boundary for app settings updates from the desktop UI."""

    def save(self, settings: AppSettings) -> None:
        """Persist application settings."""


_FIELD_LABELS = {
    "bpm": "BPM",
    "camelot_key": "Camelot key",
    "energy_level": "energy level",
}

_EMPTY_REVIEW_SUMMARY = "No recommendation is ready for review."
_RECOMMENDATION_READY_GUIDANCE = (
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist."
)
_DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT = 25
_COMPACT_LIBRARY_TABLE_MAX_HEIGHT = 150
_COMPACT_LIBRARY_TABLE_MIN_HEIGHT = 110
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
_SERATO_EXPORT_HISTORY_COLUMN_WIDTHS = (86, 110, 70, 360)
_DJ_READINESS_TABLE_COLUMN_WIDTHS = (180, 112, 520)
_READINESS_STATUS_COLORS = {"ready": "#1fd16a", "needs_review": "#ffb000", "blocked": "#ff4d4f"}
_READINESS_STATUS_TOOLTIPS = {
    "ready": "Ready: no action needed",
    "needs_review": "Needs Review: inspect before export",
    "blocked": "Blocked: fix before export",
}

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


def format_quality_summary(report: RecommendationQualityReport) -> str:
    """Return a desktop-friendly quality summary for a recommendation report."""
    return (
        "Review summary: "
        f"Tracks: {report.track_count} | "
        f"Transitions: {report.transition_count} | "
        f"Average transition score: {report.average_transition_score:.3f} | "
        f"Warnings: {report.warning_count}"
    )


def _format_review_score(score: float | None) -> str:
    """Format a transition review score or return an empty cell for unavailable scores."""
    if score is None:
        return ""
    return f"{score:.3f}"


def _score_sort_value(score: float | None) -> float:
    """Sort unavailable scores before explicit zero scores."""
    return score if score is not None else -1.0


def _format_track_tags(track: TrackRecord) -> str:
    """Return display text for tags, including parsed subgenre-style metadata."""
    return ", ".join(track.tags)


def _format_missing_metadata(track: TrackRecord) -> str:
    """Return readable missing metadata field names for incomplete-track worklists."""
    return ", ".join(
        _FIELD_LABELS.get(field_name, field_name.replace("_", " ")) for field_name in track.missing_required_fields
    )


def _missing_worklist_display_name(missing_field: str) -> str:
    """Return compact DJ-facing field labels for missing-field worklists."""
    labels = {
        "bpm": "BPM",
        "camelot_key": "Key",
        "energy_level": "Energy",
    }
    return labels.get(missing_field, missing_field.replace("_", " ").title())


def _track_vibe_terms(track: TrackRecord) -> set[str]:
    """Return normalized genre/tag terms for desktop candidate compatibility."""
    values = [*track.tags]
    if track.genre:
        values.extend(track.genre.split(","))
        values.append(track.genre)
    return {value.strip().casefold() for value in values if value.strip()}


def _track_similarity_key(
    anchor_terms: set[str],
    anchor_tracks: list[TrackRecord],
    track: TrackRecord,
) -> tuple[int, float, float, str]:
    """Sort compatible DJ candidates before unrelated fallback tracks."""
    terms = _track_vibe_terms(track)
    overlap_count = len(anchor_terms & terms)
    bpm_distance = min(
        (abs((track.bpm or 0.0) - (anchor.bpm or 0.0)) for anchor in anchor_tracks if anchor.bpm is not None),
        default=9999.0,
    )
    energy_distance = min(
        (
            abs((track.energy_level or 0) - (anchor.energy_level or 0))
            for anchor in anchor_tracks
            if anchor.energy_level is not None
        ),
        default=9999,
    )
    return (-overlap_count, bpm_distance, float(energy_distance), track.path)


def _track_review_name(track: object) -> str:
    """Return a compact track label for transition review cells."""
    title = getattr(track, "title", None)
    if title:
        return str(title)
    return str(getattr(track, "path", ""))


def _component_score(transition: object, field_name: str, component_name: str) -> float | None:
    """Read preferred explanation score fields while preserving explicit zero scores."""
    score = getattr(transition, field_name, None)
    if score is not None:
        return score
    component_scores = getattr(transition, "component_scores", {})
    return component_scores.get(component_name)


def format_recommendation_warning(raw_warning: str) -> str:
    """Return desktop-friendly text for a raw recommendation warning."""
    warning = raw_warning.strip()
    if not warning:
        return ""

    missing_marker = " missing required metadata: "
    if missing_marker in warning:
        side, _, fields_text = warning.partition(missing_marker)
        fields = [_FIELD_LABELS.get(field.strip(), field.strip().replace("_", " ")) for field in fields_text.split(",")]
        return (
            f"Review metadata: {side} track is missing Mixed In Key {', '.join(fields)} metadata. "
            "Re-scan or update tags before relying on this transition."
        )

    invalid_marker = " has invalid Camelot key: "
    if invalid_marker in warning:
        side, _, key = warning.partition(invalid_marker)
        return (
            f"Review Mixed In Key metadata: {side} track has invalid Camelot key {key!r}. "
            "Expected values look like 8A or 11B."
        )

    if warning == "invalid Camelot key":
        return "Review Mixed In Key metadata: at least one transition has an invalid Camelot key."

    return f"Review note: {warning}"


class _SortAwareTableItem(QTableWidgetItem):
    """Table item that sorts by typed values while displaying compact text."""

    def __init__(self, display_value: str, sort_value: object | None = None) -> None:
        super().__init__(display_value)
        self._sort_value = sort_value if sort_value is not None else display_value.casefold()

    def __lt__(self, other: QTableWidgetItem) -> bool:
        other_value = getattr(other, "_sort_value", other.text().casefold())
        try:
            return self._sort_value < other_value
        except TypeError:
            return str(self._sort_value).casefold() < str(other_value).casefold()


def _table_item(display_value: str, sort_value: object | None = None) -> QTableWidgetItem:
    """Build a table item with a stable display value and optional typed sort value."""
    return _SortAwareTableItem(display_value, sort_value)


class _BackgroundWorker(QObject):
    """Run one workflow operation away from the Qt UI thread."""

    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, operation: Callable[[], object]) -> None:
        super().__init__()
        self._operation = operation

    @Slot()
    def run(self) -> None:
        """Execute the operation and publish its result back to the UI thread."""
        try:
            result = self._operation()
        except Exception as exc:  # pragma: no cover - exercised through Qt signal plumbing
            self.failed.emit(exc)
            return
        self.finished.emit(result)


class _ScanWorker(QObject):
    """Run metadata scanning away from the Qt UI thread."""

    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, operation: Callable[[Callable[[ScanProgress], None]], object]) -> None:
        super().__init__()
        self._operation = operation

    @Slot()
    def run(self) -> None:
        """Execute the scan operation and publish progress/results through Qt signals."""
        try:
            result = self._operation(self.progress.emit)
        except Exception as exc:  # pragma: no cover - exercised through Qt signal plumbing
            self.failed.emit(exc)
            return
        self.finished.emit(result)


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
        self.workflow_service = PlaylistWorkflowService(scan_service=scan_service, repository=repository)
        self.settings = settings or AppSettings()
        self.settings_repository = settings_repository
        self.selected_folder: Path | None = None
        self.scanned_records: list[TrackRecord] = []
        self.last_recommendation: PlaylistRecommendation | None = None
        self.last_playlist_explanation: PlaylistExplanation | None = None
        self.last_quality_report: RecommendationQualityReport | None = None
        self.current_scan_cancellation_token: ScanCancellationToken | None = None
        self._scan_thread: QThread | None = None
        self._scan_worker: _ScanWorker | None = None
        self._recommendation_thread: QThread | None = None
        self._recommendation_worker: _BackgroundWorker | None = None
        self.serato_export_history: list[dict[str, str]] = []
        self._table_sort_orders: dict[int, Qt.SortOrder] = {}
        self._active_song_search_query = ""
        self._pre_scan_records_by_path: dict[str, TrackRecord] = {}
        self.selected_folder = self.settings.library.last_scan_folder

        self.setWindowTitle("XfinAudio")
        self.folder_button = QPushButton("Choose Folder")
        self.scan_button = QPushButton("Scan Metadata")
        self.scan_button.setEnabled(False)
        self.cancel_scan_button = QPushButton("Cancel Scan")
        self.cancel_scan_button.setEnabled(False)
        self.folder_label = QLabel("No folder selected")
        self.library_guidance_label = QLabel("Choose a Mixed In Key processed folder to scan metadata.")
        self.recommendation_guidance_label = QLabel("Scan metadata before recommending a playlist.")
        self.export_guidance_label = QLabel(
            "Review recommendations before exporting; desktop export setup is intentionally out of scope."
        )
        self.safe_export_folder_button = QPushButton("Choose Safe Export Folder")
        self.safe_export_folder_label = QLabel(self._format_safe_export_folder_label())
        self.serato_export_button = QPushButton("Export to Serato Crate")
        self.serato_export_button.setEnabled(False)
        self.scan_progress_label = QLabel("Scan progress: idle")
        self.status_label = QLabel("Ready")
        self.song_search_input = QLineEdit()
        self.song_search_input.setPlaceholderText("Search songs")
        self.song_search_input.setClearButtonEnabled(True)
        self.song_search_input.setMinimumWidth(240)
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
        self.tracks_table.itemSelectionChanged.connect(self._refresh_idle_action_state)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(available_strategies())
        self.recommend_button = QPushButton("Recommend Playlist")
        self.recommend_button.setEnabled(False)
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
        self.review_summary_label = QLabel(_EMPTY_REVIEW_SUMMARY)
        self.dj_readiness_label = QLabel("DJ Readiness: No recommendation ready.")
        self.dj_readiness_table = QTableWidget(0, 3)
        self.dj_readiness_table.setHorizontalHeaderLabels(["Check", "Status", "Detail"])
        self.transition_review_table = QTableWidget(0, len(_TRANSITION_REVIEW_HEADERS))
        self.transition_review_table.setHorizontalHeaderLabels(_TRANSITION_REVIEW_HEADERS)
        self.serato_export_history_table = QTableWidget(0, 4)
        self.serato_export_history_table.setHorizontalHeaderLabels(["Time", "Strategy", "Tracks", "Serato Crate"])
        self.serato_export_history_table.setVisible(False)
        self.folder_label.setWordWrap(False)
        self.library_guidance_label.setWordWrap(False)
        self.scan_progress_label.setWordWrap(False)
        self.recommendation_guidance_label.setWordWrap(True)
        self.export_guidance_label.setWordWrap(True)
        for label in (self.folder_label, self.library_guidance_label, self.scan_progress_label):
            label.setMaximumHeight(24)

        self.folder_button.clicked.connect(self.choose_folder)
        self.scan_button.clicked.connect(self.scan_selected_folder)
        self.cancel_scan_button.clicked.connect(self.cancel_scan)
        self.recommend_button.clicked.connect(self.recommend_playlist)
        self.safe_export_folder_button.clicked.connect(self.choose_safe_export_folder)
        self.serato_export_button.clicked.connect(lambda: self.export_recommendation_to_serato())
        self.song_search_input.textChanged.connect(lambda text: self._apply_song_filter(text, clear_selection=True))
        self.metadata_status_filter_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self.missing_metadata_filter_combo.currentTextChanged.connect(lambda _text: self._apply_song_filter())
        self.metadata_status_export_button.clicked.connect(lambda: self.export_metadata_status_to_serato())
        for table in (
            self.tracks_table,
            self.recommendation_table,
            self.transition_review_table,
            self.dj_readiness_table,
            self.serato_export_history_table,
        ):
            self._connect_table_sorting(table)
        self._apply_visual_design()

        controls = QHBoxLayout()
        controls.addWidget(self.folder_button)
        controls.addWidget(self.scan_button)
        controls.addWidget(self.cancel_scan_button)

        library_status_controls = QHBoxLayout()
        library_status_controls.addWidget(self.folder_label)
        library_status_controls.addWidget(self.library_guidance_label, 2)
        library_status_controls.addWidget(self.scan_progress_label)
        library_status_controls.addWidget(self.metadata_status_filter_combo)
        library_status_controls.addWidget(self.missing_metadata_filter_combo)
        library_status_controls.addWidget(self.song_search_input, 1)
        library_status_controls.addWidget(self.metadata_status_export_button)

        recommendation_controls = QHBoxLayout()
        recommendation_controls.addWidget(QLabel("Strategy"))
        recommendation_controls.addWidget(self.strategy_combo)
        recommendation_controls.addWidget(self.recommend_button)

        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addLayout(library_status_controls)
        layout.addWidget(self.tracks_table, 0)
        layout.addWidget(self.recommendation_guidance_label)
        layout.addLayout(recommendation_controls)
        layout.addWidget(self.recommendation_table, 2)
        layout.addWidget(self.review_summary_label)
        layout.addWidget(self.dj_readiness_label)
        layout.addWidget(self.dj_readiness_table)
        layout.addWidget(self.transition_review_table, 1)
        layout.addWidget(self.export_guidance_label)
        layout.addWidget(self.serato_export_history_table)
        layout.addWidget(self.serato_export_button)
        layout.addWidget(self.safe_export_folder_button)
        layout.addWidget(self.safe_export_folder_label)
        layout.addWidget(self.status_label)
        self._apply_compact_mac_layout(layout, controls, recommendation_controls, library_status_controls)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _apply_compact_mac_layout(
        self,
        layout: QVBoxLayout,
        controls: QHBoxLayout,
        recommendation_controls: QHBoxLayout,
        library_status_controls: QHBoxLayout,
    ) -> None:
        """Use dense desktop spacing so the library browser does not dominate MacBook screens."""
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        controls.setSpacing(8)
        library_status_controls.setSpacing(8)
        recommendation_controls.setSpacing(8)

        self.tracks_table.setMinimumHeight(_COMPACT_LIBRARY_TABLE_MIN_HEIGHT)
        self.tracks_table.setMaximumHeight(_COMPACT_LIBRARY_TABLE_MAX_HEIGHT)
        self.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
        ):
            label.setObjectName("guidanceLabel")
        for table in (
            self.tracks_table,
            self.recommendation_table,
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
        self.tracks_table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            values = [
                record.title or "",
                record.artist or "",
                "" if record.bpm is None else f"{record.bpm:g}",
                record.camelot_key or "",
                "" if record.energy_level is None else str(record.energy_level),
                _format_missing_metadata(record),
                record.genre or "",
                _format_track_tags(record),
                record.metadata_status,
                record.path,
            ]
            sort_values: list[object] = [
                values[_TRACK_TITLE_COLUMN].casefold(),
                values[1].casefold(),
                record.bpm if record.bpm is not None else float("inf"),
                values[3].casefold(),
                record.energy_level if record.energy_level is not None else 999,
                values[5].casefold(),
                values[6].casefold(),
                values[7].casefold(),
                values[_TRACK_STATUS_COLUMN].casefold(),
                values[_TRACK_PATH_COLUMN].casefold(),
            ]
            for column_index, value in enumerate(values):
                self.tracks_table.setItem(row_index, column_index, _table_item(value, sort_values[column_index]))
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
            record = next((candidate for candidate in self.scanned_records if candidate.path == path), None)
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
        return [record for record in self.scanned_records if record.metadata_status == status]

    def _metadata_missing_field_records(self, missing_field: str) -> list[TrackRecord]:
        """Return incomplete records missing the requested metadata field."""
        return [
            record
            for record in self.scanned_records
            if record.metadata_status == "incomplete" and missing_field in record.missing_required_fields
        ]

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
            self.folder_label.setText("Saved library loaded (no scan folder selected)")
            self.library_guidance_label.setText(
                "Showing saved library from the app database. Choose a folder to re-scan or update metadata."
            )
        else:
            self.folder_label.setText(f"Saved library loaded: {self.selected_folder}")
            self.library_guidance_label.setText(
                "Saved library loaded. Click Scan Metadata to refresh metadata from the last folder."
            )
        self.recommendation_guidance_label.setText(_RECOMMENDATION_READY_GUIDANCE)
        self.status_label.setText(f"Loaded saved library: {complete_count} complete, {incomplete_count} incomplete")
        self._refresh_idle_action_state()

    def _clear_scan_dependent_state(self) -> None:
        """Clear scan and recommendation results that belong to a previous folder."""
        self.scanned_records = []
        self.last_recommendation = None
        self.last_playlist_explanation = None
        self.last_quality_report = None
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

    def export_recommendation_to_serato(
        self,
        *,
        serato_folder: Path | None = None,
        crate_name: str | None = None,
    ) -> None:
        """Export the current recommendation as a confirmed Serato crate."""
        if self.last_recommendation is None:
            self.status_label.setText("Generate a recommendation before exporting to Serato")
            return

        try:
            library = (
                SeratoLibrary(serato_folder=serato_folder, volume_root=serato_folder.parent)
                if serato_folder is not None
                else select_serato_library_for_tracks(
                    [track.path for track in self.last_recommendation.ordered_tracks],
                    discover_serato_libraries(),
                )
            )
            plan = (
                plan_serato_playlist_export(crate_name, self.last_recommendation, library)
                if crate_name is not None
                else plan_generated_serato_playlist_export(self.last_recommendation, library)
            )
            result = write_serato_crate(plan, confirm=True)
        except Exception as exc:
            self.status_label.setText(f"Serato export failed: {exc}")
            return

        backup_note = (
            f" Backup: {result.backup_path}" if result.backup_path is not None else " No previous crate existed."
        )
        self.export_guidance_label.setText(
            f"Serato crate exported: {result.written_path}. "
            "Open Serato DJ Pro and check the crate under Subcrates." + backup_note
        )
        self.status_label.setText(f"Exported Serato crate: {result.written_path}")
        if self.last_quality_report is not None:
            self._show_dj_readiness(
                self.last_recommendation,
                self.last_quality_report,
                serato_plan=plan,
                serato_volume_root=library.volume_root,
            )
        self._record_serato_export(result.written_path)

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
            plan = plan_metadata_status_serato_export(records, selected_status, library)
            result = write_serato_crate(plan, confirm=True)
        except Exception as exc:
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
            self.status_label.setText(f"Serato metadata export failed: {exc}")
            return

        self.export_guidance_label.setText(
            f"Metadata worklist exported: {result.written_path}. "
            "Complete missing metadata in Serato, then click Scan Metadata in XfinAudio to refresh."
        )
        self.status_label.setText(f"Exported Missing {display_field} metadata crate: {result.written_path}")

    def _refresh_export_action_state(self) -> None:
        """Enable Serato export only when a recommendation exists."""
        self.serato_export_button.setEnabled(self.last_recommendation is not None)

    def _record_serato_export(self, written_path: Path) -> None:
        """Record a bounded in-session Serato export receipt for user verification."""
        if self.last_recommendation is None:
            return
        self.serato_export_history.insert(
            0,
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "strategy": self.last_recommendation.strategy.name,
                "tracks": str(len(self.last_recommendation.ordered_tracks)),
                "path": str(written_path),
            },
        )
        self.serato_export_history = self.serato_export_history[:_SERATO_EXPORT_HISTORY_LIMIT]
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
            ]
            sort_values: list[object] = [
                values[0],
                values[1].casefold(),
                int(values[2]),
                values[3].casefold(),
            ]
            for column_index, value in enumerate(values):
                item = _table_item(value, sort_values[column_index])
                if column_index == 3:
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
        assert self.current_scan_cancellation_token is not None
        token = self.current_scan_cancellation_token
        folder = self.selected_folder
        assert token is not None
        assert folder is not None
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
        worker = _ScanWorker(
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
        complete_records = [record for record in self.scanned_records if record.metadata_status == "complete"]
        priority_paths: list[str] = []
        if controls is not None:
            priority_paths.extend(controls.manual_order_paths)
            if controls.start_path is not None:
                priority_paths.append(controls.start_path)
            if controls.end_path is not None:
                priority_paths.append(controls.end_path)
            priority_paths.extend(sorted(controls.locked_paths))

        unique_priority_paths = list(dict.fromkeys(priority_paths))
        by_path = {record.path: record for record in complete_records}
        priority_records = [by_path[path] for path in unique_priority_paths if path in by_path]
        priority_set = {record.path for record in priority_records}
        remaining_slots = max(0, _DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT - len(priority_records))
        remaining_records = [record for record in complete_records if record.path not in priority_set]
        if not priority_records or remaining_slots == 0:
            return [*priority_records, *remaining_records[:remaining_slots]]

        anchor_terms = set().union(*(_track_vibe_terms(record) for record in priority_records))
        if not anchor_terms:
            return [*priority_records, *remaining_records[:remaining_slots]]

        terms_by_path = {record.path: _track_vibe_terms(record) for record in remaining_records}
        compatible_records = [record for record in remaining_records if anchor_terms & terms_by_path[record.path]]
        compatible_paths = {record.path for record in compatible_records}
        fallback_records = [record for record in remaining_records if record.path not in compatible_paths]
        compatible_records = sorted(
            compatible_records,
            key=lambda record: _track_similarity_key(anchor_terms, priority_records, record),
        )
        fallback_records = sorted(
            fallback_records,
            key=lambda record: _track_similarity_key(anchor_terms, priority_records, record),
        )
        return [*priority_records, *compatible_records, *fallback_records][:_DESKTOP_RECOMMENDATION_CANDIDATE_LIMIT]

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
        worker = _BackgroundWorker(lambda: self.workflow_service.recommend(records, strategy_name, controls=controls))
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
        self.recommendation_table.setRowCount(len(records))
        transition_rows = explanation.transitions if explanation is not None else []
        for row_index, record in enumerate(records):
            transition = (
                transition_rows[row_index - 1] if row_index > 0 and row_index - 1 < len(transition_rows) else None
            )
            values = [
                record.title or "",
                record.artist or "",
                "" if record.bpm is None else f"{record.bpm:g}",
                record.camelot_key or "",
                "" if record.energy_level is None else str(record.energy_level),
                record.genre or "",
                _format_track_tags(record),
                strategy_name,
                record.path,
                "" if transition is None else f"{transition.final_score:.3f}",
                ""
                if transition is None
                else "; ".join(format_recommendation_warning(warning) for warning in transition.warnings),
            ]
            sort_values: list[object] = [
                values[0].casefold(),
                values[1].casefold(),
                record.bpm if record.bpm is not None else float("inf"),
                values[3].casefold(),
                record.energy_level if record.energy_level is not None else 999,
                values[5].casefold(),
                values[6].casefold(),
                values[7].casefold(),
                values[8].casefold(),
                transition.final_score if transition is not None else -1.0,
                values[10].casefold(),
            ]
            for column_index, value in enumerate(values):
                self.recommendation_table.setItem(
                    row_index,
                    column_index,
                    _table_item(value, sort_values[column_index]),
                )

    def clear_recommendation_review(self) -> None:
        """Reset recommendation review widgets to their empty state."""
        self.review_summary_label.setText(_EMPTY_REVIEW_SUMMARY)
        self.dj_readiness_label.setText("DJ Readiness: No recommendation ready.")
        self.dj_readiness_table.setRowCount(0)
        self.transition_review_table.setRowCount(0)
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
        self.dj_readiness_label.setText(format_dj_readiness_summary(report))
        self._populate_dj_readiness_table(report)

    def _populate_dj_readiness_table(self, report: DjReadinessReport) -> None:
        """Render actionable readiness checks in a compact table."""
        self.dj_readiness_table.setRowCount(len(report.checks))
        status_labels = {"ready": "Ready", "needs_review": "Needs Review", "blocked": "Blocked"}
        status_sort = {"blocked": 0, "needs_review": 1, "ready": 2}
        for row_index, check in enumerate(report.checks):
            values = [check.label, status_labels[check.status], check.detail]
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
