"""MetadataScreen — thin QWidget for displaying metadata scan info."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.metadata_view_model import MetadataViewModel, WorklistRow
from xfinaudio.metadata.repair_guidance import explain_track_gaps, repair_plan_text

_WORKLIST_COLUMNS = ["Title", "Artist", "BPM", "Key", "Energy", "Missing", "Status"]


def _worklist_rows_signature(rows: list[WorklistRow]) -> tuple:
    """Return a comparable signature of the worklist rows shown in the table.

    render() runs on every state sync while the Metadata tab is visible, and
    rebuilding the table would wipe the DJ's selection even when the rows are
    identical. The signature covers every rendered cell value plus the UserRole
    path stored behind column 0.
    """
    return (
        len(rows),
        tuple((row.path, row.title, row.artist, row.bpm, row.key, row.energy, row.missing, row.status) for row in rows),
    )


class MetadataScreen(QWidget):
    """Displays metadata information from AppState."""

    back_requested = Signal()
    export_requested = Signal(str, str)  # (status_filter, missing_filter)
    gap_report_export_requested = Signal()
    filter_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Signature of the worklist rows currently in the table. render() runs
        # on every state sync for the visible tab, and rebuilding the table
        # would wipe the DJ's selection even when the rows are identical.
        self._last_worklist_signature: tuple | None = None
        self._repair_state = AppState()
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
        self.status_label.setMaximumHeight(28)
        layout.addWidget(self.status_label)

        # Worklist guidance
        self.guidance_label = QLabel()
        self.guidance_label.setWordWrap(True)
        self.guidance_label.setMaximumHeight(40)
        layout.addWidget(self.guidance_label)

        # Gap summary — one height-capped line above the filters so the worklist
        # table keeps the free vertical height (see the layout test).
        self.gap_summary_label = QLabel()
        self.gap_summary_label.setMaximumHeight(24)
        layout.addWidget(self.gap_summary_label)

        # Filter controls row
        filter_row = QHBoxLayout()
        self.status_combo = QComboBox()
        self.missing_combo = QComboBox()
        self.export_button = QPushButton(self.tr("Export worklist to Serato"))
        self.export_button.setToolTip(
            self.tr("Export tracks matching these metadata filters as a Serato worklist crate")
        )
        self.export_button.setEnabled(False)
        self.gap_export_button = QPushButton(self.tr("Export repair checklist"))
        self.gap_export_button.setToolTip(
            self.tr("Export the metadata gap report as JSON and CSV to the safe export folder")
        )
        self.gap_export_button.setObjectName("primaryAction")
        self.gap_export_button.setEnabled(False)
        filter_row.addWidget(self.status_combo)
        filter_row.addWidget(self.missing_combo)
        filter_row.addWidget(self.export_button)
        filter_row.addWidget(self.gap_export_button)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.repair_help_button = QPushButton(self.tr("Explain & prioritize repairs"))
        self.repair_help_button.setCheckable(True)
        self.repair_help_button.setToolTip(self.tr("Show read-only local guidance based on missing metadata"))
        self.repair_help_button.setAccessibleName(self.tr("Explain and prioritize metadata repairs"))
        layout.addWidget(self.repair_help_button)
        self.repair_help = QPlainTextEdit()
        self.repair_help.setReadOnly(True)
        self.repair_help.setMaximumHeight(150)
        self.repair_help.setAccessibleName(self.tr("Local metadata repair explanation"))
        self.repair_help.hide()
        layout.addWidget(self.repair_help)

        # Worklist table — expanding so it absorbs spare vertical space.
        self.worklist_table = QTableWidget(0, len(_WORKLIST_COLUMNS))
        self.worklist_table.setHorizontalHeaderLabels([self.tr(c) for c in _WORKLIST_COLUMNS])
        self.worklist_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.worklist_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.worklist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.worklist_table.setAlternatingRowColors(True)
        header = self.worklist_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4, 6):  # BPM, Key, Energy, Status — content-sized
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.worklist_table.verticalHeader().setVisible(False)
        self.worklist_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.worklist_table, 1)

        self.worklist_empty_label = QLabel(
            self.tr("No library scanned yet. Choose a folder on the Library tab to scan metadata.")
        )
        self.worklist_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.worklist_empty_label.setWordWrap(True)
        layout.addWidget(self.worklist_empty_label, 1)

        # No spacer here: the worklist table above carries the stretch and pushes
        # the nav row down on its own. A trailing addStretch would compete with
        # it for the free height, leaving the table about five rows tall.

        # Bottom nav
        nav = QHBoxLayout()
        self.back_button = QPushButton(self.tr("← Library"))
        self.back_button.setToolTip(self.tr("Return to the Library screen"))
        nav.addWidget(self.back_button)
        nav.addStretch()
        self.refresh_button = QPushButton(self.tr("Refresh library scan"))
        self.refresh_button.setToolTip(self.tr("Rescan the selected library after correcting tags externally"))
        self.refresh_button.setAccessibleName(self.tr("Refresh library scan"))
        nav.addWidget(self.refresh_button)
        layout.addLayout(nav)

        self._setup_accessibility()
        self._setup_tab_order()

    def _setup_accessibility(self) -> None:
        """Set accessible names for screen readers."""
        self.status_label.setAccessibleName(self.tr("Metadata status summary"))
        self.guidance_label.setAccessibleName(self.tr("Metadata worklist guidance"))
        self.gap_summary_label.setAccessibleName(self.tr("Metadata gap summary"))
        self.status_combo.setAccessibleName(self.tr("Status filter"))
        self.missing_combo.setAccessibleName(self.tr("Missing metadata filter"))
        self.export_button.setAccessibleName(self.tr("Export metadata worklist"))
        self.gap_export_button.setAccessibleName(self.tr("Export metadata gap report"))
        self.worklist_table.setAccessibleName(self.tr("Metadata worklist"))
        self.worklist_empty_label.setAccessibleName(self.tr("Metadata worklist empty state"))
        self.back_button.setAccessibleName(self.tr("Back to library"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.status_combo, self.missing_combo)
        self.setTabOrder(self.missing_combo, self.export_button)
        self.setTabOrder(self.export_button, self.gap_export_button)
        self.setTabOrder(self.gap_export_button, self.worklist_table)
        self.setTabOrder(self.worklist_table, self.back_button)
        self.setTabOrder(self.back_button, self.refresh_button)

    def _connect_signals(self) -> None:
        self.repair_help_button.toggled.connect(self.repair_help.setVisible)
        self.repair_help_button.toggled.connect(lambda _: self._render_repair_help())
        self.worklist_table.itemSelectionChanged.connect(self._render_repair_help)
        self.back_button.clicked.connect(self.back_requested)
        self.status_combo.currentTextChanged.connect(lambda _: self.filter_changed.emit())
        self.missing_combo.currentTextChanged.connect(lambda _: self.filter_changed.emit())
        self.export_button.clicked.connect(self._on_export_clicked)
        self.gap_export_button.clicked.connect(self.gap_report_export_requested)

    def connect_signals(self, window: Any) -> None:
        self.gap_report_export_requested.connect(lambda: window.export_metadata_gap_report())
        self.back_requested.connect(lambda: window.workflow_tabs.setCurrentIndex(0))
        self.refresh_button.clicked.connect(lambda: window.scan_selected_folder())
        self.filter_changed.connect(window._sync_state)
        self.export_requested.connect(window._library_controller.on_metadata_export_requested)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, state: AppState, vm: MetadataViewModel | None = None, lightweight: bool = False) -> None:
        """Update widgets from AppState via MetadataViewModel.

        Args:
            lightweight: If True, skip expensive table population
                        (used for non-visible tabs during state sync).
        """
        if vm is None:
            vm = MetadataViewModel()

        self._repair_state = state
        self.repair_help_button.setEnabled(bool(state.scanned_records))
        self.repair_help.setVisible(bool(state.scanned_records) and self.repair_help_button.isChecked())
        self._render_repair_help()
        self.status_label.setText(vm.status_text(state))
        self.gap_summary_label.setText(vm.gap_summary_text(state))
        self.gap_summary_label.setVisible(bool(state.scanned_records))

        if state.scanned_records:
            self.guidance_label.setText(
                f"{vm.worklist_guidance_text()} {vm.fix_metadata_guidance_text()} {vm.refresh_guidance_text()}"
            )
            self.guidance_label.setVisible(True)
            self.worklist_table.setVisible(True)
            self.worklist_empty_label.setVisible(False)
        else:
            self.guidance_label.setVisible(False)
            self.worklist_table.setVisible(False)
            self.worklist_empty_label.setVisible(True)

        # Populate combos once (idempotent — skip if already populated)
        if self.status_combo.count() == 0:
            with QSignalBlocker(self.status_combo):
                self.status_combo.addItems(vm.status_filter_options())
                self.status_combo.setCurrentIndex(2)  # Incomplete, including translated labels
        if self.missing_combo.count() == 0:
            with QSignalBlocker(self.missing_combo):
                self.missing_combo.addItems(vm.missing_filter_options())

        # Read current filter selections
        status_filter = self.status_combo.currentText() or None
        missing_filter = self.missing_combo.currentText() or None

        if not lightweight:
            rows = vm.worklist_rows(state, status_filter, missing_filter)
            signature = _worklist_rows_signature(rows)
            # The rowCount guard also covers direct external table clears: a
            # cleared table no longer matches the signature even when the rows
            # are unchanged, so the rebuild still happens.
            if signature != self._last_worklist_signature or self.worklist_table.rowCount() != len(rows):
                self._populate_table(rows)
                self._last_worklist_signature = signature
                self._render_repair_help()

        self.refresh_button.setEnabled(
            state.selected_folder is not None and not state.is_scanning and not state.is_recommending
        )
        self.export_button.setEnabled(vm.export_enabled(state))
        self.gap_export_button.setEnabled(vm.gap_report_export_enabled(state))

    def _render_repair_help(self) -> None:
        state = self._repair_state
        if not state.scanned_records:
            self.repair_help.clear()
            return
        selected = self.worklist_table.item(self.worklist_table.currentRow(), 0)
        path = selected.data(Qt.ItemDataRole.UserRole) if selected is not None else None
        record = next((record for record in state.scanned_records if record.path == path), None)
        if record is not None:
            text = f"{record.title or self.tr('Untitled')}\n{explain_track_gaps(record)}"
        else:
            text = repair_plan_text(state.scanned_records, locked_paths=state.locked_paths)
        self.repair_help.setPlainText(text)

    def _populate_table(self, rows: list[WorklistRow]) -> None:
        """Rebuild the worklist table, restoring same-path selection when possible.

        setRowCount(0) destroys selection and currentRow; restoring by the UserRole
        path stored on column 0 keeps the selection tied to the track, not to the
        row position, so a reordered worklist keeps the same track selected.
        """
        table = self.worklist_table
        current_item = table.item(table.currentRow(), 0)
        previous_path: str | None = None
        if current_item is not None:
            data = current_item.data(Qt.ItemDataRole.UserRole)
            if data:
                previous_path = data
        table.blockSignals(True)
        try:
            table.setRowCount(0)
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
        if previous_path:
            for row_idx in range(table.rowCount()):
                item = table.item(row_idx, 0)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == previous_path:
                    table.selectRow(row_idx)
                    break

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_export_clicked(self) -> None:
        status_filter = self.status_combo.currentText()
        missing_filter = self.missing_combo.currentText()
        self.export_requested.emit(status_filter, missing_filter)
