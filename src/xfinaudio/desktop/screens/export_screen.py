"""ExportScreen — thin QWidget that renders ExportViewModel data."""

from __future__ import annotations

from PySide6.QtCore import Signal
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
from xfinaudio.desktop.export_view_model import ExportHistoryRow, ExportViewModel

_HISTORY_COLUMNS = ["Strategy", "Tracks", "Time", "Path"]


class ExportScreen(QWidget):
    """Displays export controls and history."""

    preview_requested = Signal()
    export_requested = Signal()
    readiness_export_requested = Signal()
    safe_folder_change_requested = Signal()
    back_requested = Signal()

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

        # Variant / safe folder row
        info_row = QHBoxLayout()
        self.variant_label = QLabel()
        self.safe_folder_label = QLabel()
        self.safe_folder_button = QPushButton("Choose Folder")
        info_row.addWidget(self.variant_label)
        info_row.addStretch()
        info_row.addWidget(self.safe_folder_label)
        info_row.addWidget(self.safe_folder_button)
        layout.addLayout(info_row)

        # Action buttons
        actions = QHBoxLayout()
        self.preview_button = QPushButton("Preview")
        self.export_button = QPushButton("Export to Serato")
        self.export_button.setObjectName("seratoExportButton")
        self.export_button.setEnabled(False)
        self.export_readiness_button = QPushButton("Export Readiness Report")
        self.export_readiness_button.setEnabled(False)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.export_readiness_button)
        actions.addStretch()
        layout.addLayout(actions)

        # Export history table
        self.history_table = QTableWidget(0, len(_HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels(_HISTORY_COLUMNS)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

        # Navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton("← Review")
        nav.addWidget(self.back_button)
        nav.addStretch()
        layout.addLayout(nav)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.preview_button.clicked.connect(self.preview_requested)
        self.export_button.clicked.connect(self.export_requested)
        self.export_readiness_button.clicked.connect(self.readiness_export_requested)
        self.safe_folder_button.clicked.connect(self.safe_folder_change_requested)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: ExportViewModel, state: AppState) -> None:
        """Update all widgets from ViewModel data."""
        self.variant_label.setText(vm.applied_variant_label(state))
        self.safe_folder_label.setText(vm.safe_folder_label(state))
        self.export_button.setEnabled(vm.export_enabled(state))
        self.export_readiness_button.setEnabled(vm.export_readiness_enabled(state))
        self._populate_history_table(vm.export_history_rows(state))

    def _populate_history_table(self, rows: list[ExportHistoryRow]) -> None:
        self.history_table.setRowCount(0)
        for row_data in rows:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            values = [
                row_data.crate_name,
                row_data.track_count,
                row_data.exported_at,
                row_data.destination,
            ]
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, QTableWidgetItem(str(value)))
