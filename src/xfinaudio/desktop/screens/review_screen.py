"""ReviewScreen — thin QWidget that renders ReviewViewModel data."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.review_view_model import (
    ReadinessCheckRow,
    RecommendationRow,
    ReviewViewModel,
)

_READINESS_COLUMNS = ["Check", "Status", "Detail"]
_RECOMMENDATION_COLUMNS = ["#", "Title", "Artist", "BPM", "Key", "Energy", "Score"]
_TRANSITION_COLUMNS = [
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


class ReviewScreen(QWidget):
    """Displays readiness status, track list, and transition analysis."""

    back_requested = Signal()
    proceed_to_export_requested = Signal()
    track_remove_requested = Signal(str)  # emits the track path
    track_play_requested = Signal(str)  # emits the track path

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Readiness badge — primary semaphore, large and prominent
        self.readiness_badge = QLabel()
        self.readiness_badge.setObjectName("readinessBadge")
        layout.addWidget(self.readiness_badge)

        # DJ readiness summary (set imperatively by main_window)
        self.dj_readiness_label = QLabel("DJ Readiness: No recommendation ready.")
        layout.addWidget(self.dj_readiness_label)

        # Quality summary (set imperatively by main_window)
        self.review_summary_label = QLabel("No recommendation is ready for review.")
        layout.addWidget(self.review_summary_label)

        # VM-driven quality summary
        self.quality_label = QLabel()
        layout.addWidget(self.quality_label)

        # Readiness checks table
        self.readiness_table = QTableWidget(0, len(_READINESS_COLUMNS))
        self.readiness_table.setHorizontalHeaderLabels(_READINESS_COLUMNS)
        self.readiness_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.readiness_table.setAlternatingRowColors(True)
        layout.addWidget(self.readiness_table)

        # Recommendation table
        self.recommendation_table = QTableWidget(0, len(_RECOMMENDATION_COLUMNS))
        self.recommendation_table.setHorizontalHeaderLabels(_RECOMMENDATION_COLUMNS)
        self.recommendation_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.recommendation_table.setAlternatingRowColors(True)
        layout.addWidget(self.recommendation_table)

        # Action row for the recommendation table
        actions = QHBoxLayout()
        self.remove_track_button = QPushButton("Remove from Playlist")
        self.remove_track_button.setEnabled(False)
        actions.addWidget(self.remove_track_button)
        actions.addStretch()
        layout.addLayout(actions)

        # Transition table
        self.transition_table = QTableWidget(0, len(_TRANSITION_COLUMNS))
        self.transition_table.setHorizontalHeaderLabels(_TRANSITION_COLUMNS)
        self.transition_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transition_table.setAlternatingRowColors(True)
        layout.addWidget(self.transition_table)

        # Navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton("← Build")
        self.export_button = QPushButton("Export →")
        self.export_button.setObjectName("primaryAction")
        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.export_button)
        layout.addLayout(nav)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.export_button.clicked.connect(self.proceed_to_export_requested)
        self.recommendation_table.itemSelectionChanged.connect(self._on_recommendation_selection_changed)
        self.remove_track_button.clicked.connect(self._on_remove_clicked)
        self.recommendation_table.itemDoubleClicked.connect(self._on_rec_double_clicked)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: ReviewViewModel, state: AppState) -> None:
        """Update all widgets from ViewModel data."""
        self.readiness_badge.setText(vm.readiness_badge_text(state))
        self.quality_label.setText(vm.quality_summary(state))
        self.export_button.setEnabled(vm.can_export(state))
        self._populate_recommendation_table(vm.recommendation_rows(state))
        # readiness_table and transition_table are populated imperatively by
        # _populate_dj_readiness_table / show_transition_review / clear_recommendation_review

    def _populate_readiness_table(self, rows: list[ReadinessCheckRow]) -> None:
        self.readiness_table.setRowCount(0)
        for row_data in rows:
            row = self.readiness_table.rowCount()
            self.readiness_table.insertRow(row)
            for col, value in enumerate([row_data.label, row_data.status, row_data.detail]):
                self.readiness_table.setItem(row, col, QTableWidgetItem(value))

    def _populate_recommendation_table(self, rows: list[RecommendationRow]) -> None:
        self.recommendation_table.setRowCount(0)
        for row_data in rows:
            row = self.recommendation_table.rowCount()
            self.recommendation_table.insertRow(row)
            values = [
                str(row_data.position),
                row_data.title,
                row_data.artist,
                row_data.bpm,
                row_data.camelot_key,
                row_data.energy,
                row_data.overall_score,
            ]
            for col, value in enumerate(values):
                self.recommendation_table.setItem(row, col, QTableWidgetItem(value))
            # Store path as UserRole on col 0 for removal and play actions
            position_item = self.recommendation_table.item(row, 0)
            if position_item is not None:
                position_item.setData(Qt.ItemDataRole.UserRole, row_data.path)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_recommendation_selection_changed(self) -> None:
        self.remove_track_button.setEnabled(bool(self.recommendation_table.selectedItems()))

    def _on_remove_clicked(self) -> None:
        selected = self.recommendation_table.selectedItems()
        if not selected:
            return
        row = self.recommendation_table.currentRow()
        path_item = self.recommendation_table.item(row, 0)
        if path_item is None:
            return
        path = path_item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.track_remove_requested.emit(path)

    def _on_rec_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        path_item = self.recommendation_table.item(row, 0)
        if path_item is None:
            return
        path = path_item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.track_play_requested.emit(path)
