"""ReviewScreen — thin QWidget that renders ReviewViewModel data."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
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
_RECOMMENDATION_COLUMNS = ["#", "Title", "Artist", "BPM", "Key", "Energy", "Color"]
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

# Header tooltips for the transition review table
_TRANSITION_HEADER_TOOLTIPS = {
    0: "Position of this transition in the playlist",
    1: "First track in the transition",
    2: "Second track in the transition",
    3: (
        "Tonal compatibility (Camelot). 1.0 = same key, 0.9 = adjacent or diagonal, "
        "0.85 = relative A/B, 0.0 = incompatible"
    ),
    4: "BPM similarity. 1.0 = ≤2% difference, drops as the gap grows",
    5: "Energy level similarity. 1.0 = same energy, drops as levels diverge",
    6: "Genre/tag overlap. Higher = more shared tags or genres",
    7: "Weighted average: 60% Key + 20% BPM + 15% Energy + 5% Tags",
    8: "Alerts about potential issues in this transition",
}

_READINESS_HEADER_TOOLTIPS = {
    0: "Category being validated",
    1: "Ready, Needs Review, or Blocked",
    2: "Specific explanation for this check",
}

# Color coding for score cells
_SCORE_COLOR_EXCELLENT = QColor("#1a3a2a")
_SCORE_COLOR_GOOD = QColor("#3a3010")
_SCORE_COLOR_POOR = QColor("#4a1a1a")
_SCORE_TEXT_EXCELLENT = QColor("#1fd16a")
_SCORE_TEXT_GOOD = QColor("#ffb000")
_SCORE_TEXT_POOR = QColor("#ff4d4f")


class ReviewScreen(QWidget):
    """Displays readiness status, track list, and transition analysis."""

    back_requested = Signal()
    proceed_to_export_requested = Signal()
    save_to_playlists_requested = Signal()
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

        # 1. Decision banner — primary semaphore, large and prominent
        self.readiness_badge = QLabel()
        self.readiness_badge.setObjectName("readinessBadge")
        layout.addWidget(self.readiness_badge)

        # 2. Reason summary — keep compact so tables get space
        self.dj_readiness_label = QLabel(self.tr("DJ Readiness: No recommendation ready."))
        self.dj_readiness_label.setMaximumHeight(28)
        layout.addWidget(self.dj_readiness_label)

        # Quality summary (set imperatively by main_window)
        self.review_summary_label = QLabel(self.tr("No recommendation is ready for review."))
        self.review_summary_label.setMaximumHeight(28)
        layout.addWidget(self.review_summary_label)

        # VM-driven quality summary
        self.quality_label = QLabel()
        self.quality_label.setMaximumHeight(28)
        layout.addWidget(self.quality_label)

        # 3. Recommendation table
        self.recommendation_table = QTableWidget(0, len(_RECOMMENDATION_COLUMNS))
        self.recommendation_table.setHorizontalHeaderLabels([self.tr(c) for c in _RECOMMENDATION_COLUMNS])
        header = self.recommendation_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in (0, 3, 4, 5):  # #, BPM, Key, Energy — content-sized
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.recommendation_table.setAlternatingRowColors(True)
        self.recommendation_table.verticalHeader().setVisible(False)
        self.recommendation_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.recommendation_table, 1)

        # Action row for the recommendation table
        actions = QHBoxLayout()
        self.remove_track_button = QPushButton(self.tr("Remove from Playlist"))
        self.remove_track_button.setEnabled(False)
        actions.addWidget(self.remove_track_button)
        self.save_to_playlists_button = QPushButton(self.tr("Save to My Playlists"))
        self.save_to_playlists_button.setEnabled(False)
        actions.addWidget(self.save_to_playlists_button)
        actions.addStretch()
        layout.addLayout(actions)

        # 4. Transition table help label
        self.transition_help_label = QLabel(
            self.tr(
                "💡 Each row shows how two consecutive tracks blend. "
                "Green = excellent, Yellow = acceptable, Red = risky. "
                "Hover over any score for details."
            )
        )
        self.transition_help_label.setWordWrap(True)
        self.transition_help_label.setMaximumHeight(40)
        self.transition_help_label.setStyleSheet("color: #9fb3c8; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.transition_help_label)

        # 5. Transition table
        self.transition_table = QTableWidget(0, len(_TRANSITION_COLUMNS))
        self.transition_table.setHorizontalHeaderLabels([self.tr(c) for c in _TRANSITION_COLUMNS])
        self.transition_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transition_table.setAlternatingRowColors(True)
        self.transition_table.verticalHeader().setVisible(False)
        self.transition_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_header_tooltips(self.transition_table, _TRANSITION_HEADER_TOOLTIPS)
        layout.addWidget(self.transition_table, 1)

        # 6. Readiness checks table (secondary)
        self.readiness_table = QTableWidget(0, len(_READINESS_COLUMNS))
        self.readiness_table.setHorizontalHeaderLabels([self.tr(c) for c in _READINESS_COLUMNS])
        self.readiness_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.readiness_table.setAlternatingRowColors(True)
        self.readiness_table.verticalHeader().setVisible(False)
        self.readiness_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_header_tooltips(self.readiness_table, _READINESS_HEADER_TOOLTIPS)
        layout.addWidget(self.readiness_table, 1)

        # Push nav to bottom; spare space goes to tables above.
        layout.addStretch(1)

        # Navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton(self.tr("← Build"))
        self.export_button = QPushButton(self.tr("Export →"))
        self.export_button.setObjectName("primaryAction")
        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.export_button)
        layout.addLayout(nav)

        self._setup_accessibility()
        self._setup_tab_order()

    def _setup_accessibility(self) -> None:
        """Set accessible names for screen readers."""
        self.readiness_badge.setAccessibleName(self.tr("DJ readiness badge"))
        self.dj_readiness_label.setAccessibleName(self.tr("DJ readiness summary"))
        self.recommendation_table.setAccessibleName(self.tr("Recommended playlist"))
        self.remove_track_button.setAccessibleName(self.tr("Remove selected track from playlist"))
        self.save_to_playlists_button.setAccessibleName(self.tr("Save recommendation to My Playlists"))
        self.transition_table.setAccessibleName(self.tr("Transition analysis"))
        self.readiness_table.setAccessibleName(self.tr("Readiness checks"))
        self.back_button.setAccessibleName(self.tr("Back to build"))
        self.export_button.setAccessibleName(self.tr("Proceed to export"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.readiness_badge, self.recommendation_table)
        self.setTabOrder(self.recommendation_table, self.remove_track_button)
        self.setTabOrder(self.remove_track_button, self.save_to_playlists_button)
        self.setTabOrder(self.save_to_playlists_button, self.transition_table)
        self.setTabOrder(self.transition_table, self.readiness_table)
        self.setTabOrder(self.readiness_table, self.back_button)
        self.setTabOrder(self.back_button, self.export_button)

    def _apply_header_tooltips(self, table: QTableWidget, tooltips: dict[int, str]) -> None:
        for column_index, text in tooltips.items():
            header_item = table.horizontalHeaderItem(column_index)
            if header_item is None:
                header_item = QTableWidgetItem()
            if header_item is not None:
                header_item.setToolTip(self.tr(text))
                table.setHorizontalHeaderItem(column_index, header_item)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.export_button.clicked.connect(self.proceed_to_export_requested)
        self.save_to_playlists_button.clicked.connect(self.save_to_playlists_requested)
        self.recommendation_table.itemSelectionChanged.connect(self._on_recommendation_selection_changed)
        self.remove_track_button.clicked.connect(self._on_remove_clicked)
        self.recommendation_table.itemDoubleClicked.connect(self._on_rec_double_clicked)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: ReviewViewModel, state: AppState, lightweight: bool = False) -> None:
        """Update all widgets from ViewModel data.

        Args:
            lightweight: If True, skip expensive recommendation table population
                        (used for non-visible tabs during state sync).
        """
        self.readiness_badge.setText(vm.readiness_badge_text(state))
        self.quality_label.setText(vm.quality_summary(state))
        self.export_button.setEnabled(vm.can_export(state))
        self.save_to_playlists_button.setEnabled(state.last_recommendation is not None)
        if not lightweight:
            self._populate_recommendation_table(vm.recommendation_rows(state))
        # readiness_table and transition_table are populated imperatively by
        # _populate_dj_readiness_table / show_transition_review / clear_recommendation_review

    def _populate_readiness_table(self, rows: list[ReadinessCheckRow]) -> None:
        self.readiness_table.setRowCount(0)
        for row_data in rows:
            row = self.readiness_table.rowCount()
            self.readiness_table.insertRow(row)
            label_item = QTableWidgetItem(row_data.label)
            label_item.setToolTip(self.tr("Validation: {0}").format(row_data.label))
            status_item = QTableWidgetItem(row_data.status)
            status_item.setToolTip(self.tr("Status: {0}").format(row_data.status))
            detail_item = QTableWidgetItem(row_data.detail)
            detail_item.setToolTip(row_data.detail)
            self.readiness_table.setItem(row, 0, label_item)
            self.readiness_table.setItem(row, 1, status_item)
            self.readiness_table.setItem(row, 2, detail_item)

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
                row_data.spectral_color,
            ]
            tooltips = [
                self.tr("Track #{0} in playlist").format(row_data.position),
                row_data.title,
                row_data.artist,
                self.tr("BPM: {0}").format(row_data.bpm),
                self.tr("Camelot key: {0}").format(row_data.camelot_key),
                self.tr("Energy level: {0}").format(row_data.energy),
                self.tr("Spectral color: {0}").format(row_data.spectral_color),
            ]
            for col, (value, tip) in enumerate(zip(values, tooltips, strict=True)):
                item = QTableWidgetItem(value)
                item.setToolTip(tip)
                self.recommendation_table.setItem(row, col, item)
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
