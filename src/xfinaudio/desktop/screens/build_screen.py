"""BuildScreen — thin QWidget that renders BuildViewModel data."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel, CopilotVariantRow

_READINESS_STATUS_LABELS = {"ready": "Ready", "needs_review": "Needs Review", "blocked": "Blocked"}
_READINESS_STATUS_COLORS = {"ready": "#1fd16a", "needs_review": "#ffb000", "blocked": "#ff4d4f"}

_COPILOT_COLUMNS = ["Variant", "Description", "Tracks", "Readiness"]


class BuildScreen(QWidget):
    """Displays strategy selection and Prep Copilot controls."""

    recommend_requested = Signal(str, list)
    copilot_generate_requested = Signal()
    copilot_variant_applied = Signal(int)
    back_requested = Signal()
    exclude_requested = Signal()
    lock_requested = Signal()
    clear_constraints_requested = Signal()

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

        # Strategy row
        strategy_row = QHBoxLayout()
        self.strategy_combo = QComboBox()
        self.recommend_button = QPushButton("Recommend Playlist")
        self.recommend_button.setEnabled(False)
        strategy_row.addWidget(self.strategy_combo)
        strategy_row.addWidget(self.recommend_button)
        strategy_row.addStretch()
        layout.addLayout(strategy_row)

        # Constraints row
        constraints_row = QHBoxLayout()
        self.exclude_button = QPushButton("Exclude Selected")
        self.lock_button = QPushButton("Lock Selected")
        self.clear_constraints_button = QPushButton("Clear Constraints")
        self.clear_constraints_button.setEnabled(False)
        self.constraints_label = QLabel("")
        constraints_row.addWidget(self.exclude_button)
        constraints_row.addWidget(self.lock_button)
        constraints_row.addWidget(self.clear_constraints_button)
        constraints_row.addWidget(self.constraints_label)
        constraints_row.addStretch()
        layout.addLayout(constraints_row)

        # Copilot section
        copilot_row = QHBoxLayout()
        self.target_count_input = QSpinBox()
        self.target_count_input.setRange(2, 100)
        self.target_count_input.setValue(25)
        self.genre_focus_input = QLineEdit()
        self.genre_focus_input.setPlaceholderText("Genre focus")
        self.copilot_button = QPushButton("Generate Prep Copilot")
        self.variant_label = QLabel()
        copilot_row.addWidget(QLabel("Set Tracks"))
        copilot_row.addWidget(self.target_count_input)
        copilot_row.addWidget(self.genre_focus_input)
        copilot_row.addWidget(self.copilot_button)
        copilot_row.addWidget(self.variant_label)
        copilot_row.addStretch()
        layout.addLayout(copilot_row)

        # Copilot variants table
        self.copilot_table = QTableWidget(0, len(_COPILOT_COLUMNS))
        self.copilot_table.setHorizontalHeaderLabels(_COPILOT_COLUMNS)
        self.copilot_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.copilot_table.setAlternatingRowColors(True)
        self.copilot_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.copilot_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.copilot_table)

        # Applied variant badge (set imperatively by main_window)
        self.applied_copilot_variant_label = QLabel("Applied Variant: none")
        self.applied_copilot_variant_label.setToolTip("No Prep Copilot variant is currently applied.")
        layout.addWidget(self.applied_copilot_variant_label)

        # Apply variant button
        self.apply_variant_button = QPushButton("Apply Selected Variant")
        layout.addWidget(self.apply_variant_button)

        # Bottom navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton("← Library")
        self.proceed_button = QPushButton("Review →")
        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.proceed_button)
        layout.addLayout(nav)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.copilot_button.clicked.connect(self.copilot_generate_requested)
        self.apply_variant_button.clicked.connect(self._on_apply_variant)
        self.recommend_button.clicked.connect(self._on_recommend)
        self.exclude_button.clicked.connect(self.exclude_requested)
        self.lock_button.clicked.connect(self.lock_requested)
        self.clear_constraints_button.clicked.connect(self.clear_constraints_requested)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: BuildViewModel, state: AppState) -> None:
        """Update all widgets from ViewModel data."""
        # Populate strategy combo (only if empty to avoid clearing user selection)
        if self.strategy_combo.count() == 0:
            for option in vm.available_strategies():
                self.strategy_combo.addItem(option.name)

        # recommend_button enabled state is managed by MainWindow._refresh_idle_action_state
        self.copilot_button.setEnabled(vm.copilot_button_enabled(state))
        self.variant_label.setText(vm.applied_variant_label(state))
        self.proceed_button.setEnabled(vm.can_proceed(state))
        rows = vm.copilot_variants_for_display(state)
        self._populate_copilot_table(rows)
        self.copilot_table.setHidden(len(rows) == 0)

        excluded = len(state.excluded_paths)
        locked = len(state.locked_paths)
        parts = []
        if excluded:
            parts.append(f"{excluded} excluded")
        if locked:
            parts.append(f"{locked} locked")
        self.constraints_label.setText(", ".join(parts) if parts else "")
        self.clear_constraints_button.setEnabled(bool(excluded or locked))

    def _populate_copilot_table(self, rows: list[CopilotVariantRow]) -> None:
        self.copilot_table.setRowCount(0)
        for row_data in rows:
            row = self.copilot_table.rowCount()
            self.copilot_table.insertRow(row)
            status = row_data.readiness_status
            readiness_label = _READINESS_STATUS_LABELS.get(status, status)
            values = [
                row_data.name,
                row_data.description,
                str(row_data.track_count),
                readiness_label,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    color = _READINESS_STATUS_COLORS.get(status)
                    if color:
                        item.setBackground(QColor(color))
                        item.setForeground(QColor("#061016"))
                    item.setToolTip(row_data.readiness_summary)
                self.copilot_table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_recommend(self) -> None:
        strategy = self.strategy_combo.currentText()
        self.recommend_requested.emit(strategy, [])

    def _on_apply_variant(self) -> None:
        selected_rows = self.copilot_table.selectedItems()
        if not selected_rows:
            return
        row = self.copilot_table.currentRow()
        self.copilot_variant_applied.emit(row)
