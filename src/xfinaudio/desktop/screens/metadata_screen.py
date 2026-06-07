"""MetadataScreen — thin QWidget for displaying metadata scan info."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.metadata_view_model import MetadataViewModel

_WORKLIST_COLUMNS = ["Title", "Artist", "BPM", "Key", "Energy", "Missing", "Status"]


class MetadataScreen(QWidget):
    """Displays metadata information from AppState."""

    back_requested = Signal()
    export_requested = Signal(str, str)  # (status_filter, missing_filter)
    filter_changed = Signal()

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

        # Status summary
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Worklist guidance
        self.guidance_label = QLabel()
        self.guidance_label.setWordWrap(True)
        layout.addWidget(self.guidance_label)

        # Filter controls row
        filter_row = QHBoxLayout()
        self.status_combo = QComboBox()
        self.missing_combo = QComboBox()
        self.export_button = QPushButton("Export to Serato")
        self.export_button.setEnabled(False)
        filter_row.addWidget(self.status_combo)
        filter_row.addWidget(self.missing_combo)
        filter_row.addWidget(self.export_button)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Worklist table
        self.worklist_table = QTableWidget(0, len(_WORKLIST_COLUMNS))
        self.worklist_table.setHorizontalHeaderLabels(_WORKLIST_COLUMNS)
        self.worklist_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.worklist_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.worklist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.worklist_table.setAlternatingRowColors(True)
        self.worklist_table.horizontalHeader().setStretchLastSection(True)
        self.worklist_table.verticalHeader().setVisible(False)
        layout.addWidget(self.worklist_table)

        # Bottom nav
        nav = QHBoxLayout()
        self.back_button = QPushButton("← Library")
        nav.addWidget(self.back_button)
        nav.addStretch()
        layout.addLayout(nav)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.status_combo.currentTextChanged.connect(lambda _: self.filter_changed.emit())
        self.missing_combo.currentTextChanged.connect(lambda _: self.filter_changed.emit())
        self.export_button.clicked.connect(self._on_export_clicked)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, state: AppState, vm: MetadataViewModel | None = None) -> None:
        """Update widgets from AppState via MetadataViewModel."""
        if vm is None:
            vm = MetadataViewModel()

        self.status_label.setText(vm.status_text(state))

        if state.scanned_records:
            self.guidance_label.setText(
                f"{vm.worklist_guidance_text()} {vm.fix_metadata_guidance_text()} {vm.refresh_guidance_text()}"
            )
            self.guidance_label.setVisible(True)
        else:
            self.guidance_label.setVisible(False)

        # Populate combos once (idempotent — skip if already populated)
        if self.status_combo.count() == 0:
            self.status_combo.addItems(vm.status_filter_options())
        if self.missing_combo.count() == 0:
            self.missing_combo.addItems(vm.missing_filter_options())

        # Read current filter selections
        status_filter = self.status_combo.currentText() or None
        missing_filter = self.missing_combo.currentText() or None

        rows = vm.worklist_rows(state, status_filter, missing_filter)
        self._populate_table(rows)

        self.export_button.setEnabled(vm.export_enabled(state))

    def _populate_table(self, rows: list) -> None:
        self.worklist_table.blockSignals(True)
        try:
            self.worklist_table.setRowCount(0)
            for row_data in rows:
                row_idx = self.worklist_table.rowCount()
                self.worklist_table.insertRow(row_idx)
                values = [
                    row_data.title,
                    row_data.artist,
                    row_data.bpm,
                    row_data.key,
                    row_data.energy,
                    row_data.missing,
                    row_data.status,
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    # Store full path as hidden data for export lookups
                    if col == 0:
                        item.setData(Qt.ItemDataRole.UserRole, row_data.path)
                    self.worklist_table.setItem(row_idx, col, item)
        finally:
            self.worklist_table.blockSignals(False)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_export_clicked(self) -> None:
        status_filter = self.status_combo.currentText()
        missing_filter = self.missing_combo.currentText()
        self.export_requested.emit(status_filter, missing_filter)
