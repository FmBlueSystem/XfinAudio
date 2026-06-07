"""LibraryScreen — thin QWidget that renders LibraryViewModel data."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryViewModel, TrackDisplayRow

_COLUMNS = ["Title", "Artist", "BPM", "Key", "Energy", "Missing", "Genre", "Status", "Path"]


class LibraryScreen(QWidget):
    """Displays the track library and scan controls."""

    folder_change_requested = Signal()
    scan_requested = Signal()
    cancel_scan_requested = Signal()
    selection_changed = Signal(list)
    metadata_screen_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._filter_query: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top controls row
        controls = QHBoxLayout()
        self.folder_button = QPushButton("Choose Folder")
        self.scan_button = QPushButton("Scan Library")
        self.cancel_button = QPushButton("Cancel")
        controls.addWidget(self.folder_button)
        controls.addWidget(self.scan_button)
        controls.addWidget(self.cancel_button)
        controls.addStretch()
        layout.addLayout(controls)

        # Status
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks…")
        layout.addWidget(self.search_input)

        # Table
        self.tracks_table = QTableWidget(0, len(_COLUMNS))
        self.tracks_table.setHorizontalHeaderLabels(_COLUMNS)
        self.tracks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tracks_table.setAlternatingRowColors(True)
        self.tracks_table.setSelectionBehavior(self.tracks_table.SelectionBehavior.SelectRows)
        layout.addWidget(self.tracks_table)

        # Bottom row
        bottom = QHBoxLayout()
        self.proceed_button = QPushButton("Build Playlist →")
        bottom.addStretch()
        bottom.addWidget(self.proceed_button)
        layout.addLayout(bottom)

    def _connect_signals(self) -> None:
        self.folder_button.clicked.connect(self.folder_change_requested)
        self.scan_button.clicked.connect(self.scan_requested)
        self.cancel_button.clicked.connect(self.cancel_scan_requested)
        self.tracks_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.search_input.textChanged.connect(self._on_search_changed)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: LibraryViewModel, state: AppState) -> None:
        """Update all widgets from ViewModel data."""
        self.scan_button.setEnabled(vm.scan_button_enabled(state))
        self.cancel_button.setVisible(vm.cancel_button_visible(state))
        self.status_label.setText(vm.status_text(state))
        self.proceed_button.setEnabled(vm.can_proceed(state))
        self._populate_table(vm.tracks_for_display(state))
        self._apply_filter()

    def _populate_table(self, rows: list[TrackDisplayRow]) -> None:
        self.tracks_table.blockSignals(True)
        try:
            self.tracks_table.setRowCount(0)
            for row_data in rows:
                row = self.tracks_table.rowCount()
                self.tracks_table.insertRow(row)
                values = [
                    row_data.title,
                    row_data.artist,
                    row_data.bpm,
                    row_data.musical_key,
                    row_data.energy,
                    row_data.missing_fields,
                    row_data.genre,
                    row_data.metadata_status,
                    row_data.path,  # full path for lookup; display_path only for UI labels
                ]
                for col, value in enumerate(values):
                    self.tracks_table.setItem(row, col, QTableWidgetItem(value))
        finally:
            self.tracks_table.blockSignals(False)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str) -> None:
        self._filter_query = text.strip().casefold()
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self._filter_query
        for row in range(self.tracks_table.rowCount()):
            title_item = self.tracks_table.item(row, 0)
            title = (title_item.text() if title_item else "").casefold()
            self.tracks_table.setRowHidden(row, bool(query) and query not in title)

    def _on_selection_changed(self) -> None:
        selected_rows = {idx.row() for idx in self.tracks_table.selectedIndexes()}
        paths: list[str] = []
        for row in selected_rows:
            path_item = self.tracks_table.item(row, len(_COLUMNS) - 1)
            if path_item is not None:
                paths.append(path_item.text())
        self.selection_changed.emit(paths)
