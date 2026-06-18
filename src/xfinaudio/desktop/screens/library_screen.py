"""LibraryScreen — thin QWidget that renders LibraryViewModel data."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryFilters, LibraryViewModel, TrackDisplayRow
from xfinaudio.desktop.scan_service import progress_percent, progress_status_text

_EMPTY = QTableWidgetItem("")
_ROW_COLOR_EVEN = QColor("#101820")
_ROW_COLOR_ODD = QColor("#14202a")
_ROW_COLOR_SELECTED = QColor("#0078b4")

_COLUMNS = [
    "Title",
    "Artist",
    "BPM",
    "Key",
    "Energy",
    "Duration",
    "Color",
    "Missing",
    "Genre",
    "Status",
    "Preview",
    "Path",
]
_MISSING_COLUMN = _COLUMNS.index("Missing")


def _sort_key_for_column(row: TrackDisplayRow, column: int) -> Any:
    """Return a sortable value for *row* according to *column*."""
    if column == 0:
        return row.title.casefold()
    if column == 1:
        return row.artist.casefold()
    if column == 2:
        return float("inf") if row.bpm == "—" else float(row.bpm)
    if column == 3:
        return row.musical_key.casefold()
    if column == 4:
        return float("inf") if row.energy == "—" else int(row.energy)
    if column == 5:
        # Parse "M:SS" duration into total seconds for sorting
        if row.duration == "—":
            return float("inf")
        parts = row.duration.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    if column == 6:
        return row.spectral_color.casefold()
    if column == 7:
        return row.missing_fields.casefold()
    if column == 8:
        return row.genre.casefold()
    if column == 9:
        return row.metadata_status.casefold()
    if column == 10:
        return ""  # Preview column — not sortable
    if column == 11:
        return row.path.casefold()
    return ""


class LibraryScreen(QWidget):
    """Displays the track library and scan controls."""

    folder_change_requested = Signal()
    scan_requested = Signal()
    cancel_scan_requested = Signal()
    selection_changed = Signal(list)
    metadata_screen_requested = Signal()
    settings_requested = Signal()
    track_play_requested = Signal(str)  # emits full path
    play_requested = Signal(str)
    pause_requested = Signal()
    filters_cleared = Signal(list)  # emits labels of filters that were active before clearing

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sort_column: int | None = None
        self._sort_ascending: bool = True
        self._last_vm: LibraryViewModel | None = None
        self._last_state: AppState | None = None
        self._playing_path: str | None = None
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._filter_query: str = ""
        self._missing_column_visible = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top controls row
        controls = QHBoxLayout()
        self.folder_button = QPushButton(self.tr("Choose Folder"))
        self.scan_button = QPushButton(self.tr("Scan Metadata"))
        self.scan_button.setObjectName("primaryAction")
        self.scan_button.setMinimumHeight(36)
        self.cancel_button = QPushButton(self.tr("Cancel Scan"))
        self.cancel_button.setObjectName("secondaryAction")
        self.cancel_button.setMaximumHeight(26)
        self.missing_column_button = QPushButton(self.tr("Show Missing"))
        self.cancel_button.setEnabled(False)
        controls.addWidget(self.folder_button)
        controls.addWidget(self.scan_button)
        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setRange(0, 100)
        self.scan_progress_bar.setTextVisible(False)
        self.scan_progress_bar.setVisible(False)
        self.scan_progress_label = QLabel("")
        self.scan_progress_label.setVisible(False)
        controls.addWidget(self.scan_progress_bar)
        controls.addWidget(self.scan_progress_label)
        controls.addWidget(self.cancel_button)
        controls.addWidget(self.missing_column_button)
        controls.addStretch()
        layout.addLayout(controls)

        # Scan settings review
        self.scan_settings_label = QLabel()
        self.scan_settings_label.setWordWrap(True)
        layout.addWidget(self.scan_settings_label)

        # Status
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Search songs"))
        self.search_input.setMinimumWidth(160)
        self.search_input.setMaximumWidth(220)
        layout.addWidget(self.search_input)

        self.quick_filter_layout = QHBoxLayout()
        (
            self.complete_filter_button,
            self.incomplete_filter_button,
            self.missing_bpm_filter_button,
            self.missing_key_filter_button,
            self.missing_energy_filter_button,
        ) = (
            QPushButton(self.tr(label))
            for label in ("Complete", "Incomplete", "Missing BPM", "Missing Key", "Missing Energy")
        )
        self.quick_filter_buttons = (
            self.complete_filter_button,
            self.incomplete_filter_button,
            self.missing_bpm_filter_button,
            self.missing_key_filter_button,
            self.missing_energy_filter_button,
        )
        self.clear_filters_button = QPushButton(self.tr("Clear Filters"))
        self.active_filter_count_label = QLabel(self.tr("0 active"))
        for button in self.quick_filter_buttons:
            button.setCheckable(True)
            button.setStyleSheet("QPushButton:checked { background: #00d4ff; color: #061018; border-color: #00d4ff; }")
            self.quick_filter_layout.addWidget(button)
        self.quick_filter_layout.addWidget(self.clear_filters_button)
        self.quick_filter_layout.addWidget(self.active_filter_count_label)
        self.quick_filter_layout.addStretch()
        layout.addLayout(self.quick_filter_layout)

        # Section divider between controls and table
        self.section_divider = QFrame()
        self.section_divider.setObjectName("sectionDivider")
        self.section_divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.section_divider)

        # Empty-state guidance (no library / no tracks)
        self.empty_state_label = QLabel()
        self.empty_state_label.setObjectName("guidanceLabel")
        self.empty_state_label.setWordWrap(True)
        layout.addWidget(self.empty_state_label)

        # Table
        self.tracks_table = QTableWidget(0, len(_COLUMNS))
        self.tracks_table.setHorizontalHeaderLabels([self.tr(c) for c in _COLUMNS])
        header = self.tracks_table.horizontalHeader()
        # Header tooltips explain each column to novice DJs.
        _HEADER_TOOLTIPS = [
            "Track title from audio metadata",
            "Artist or performer name",
            "Beats per minute — tempo of the track",
            "Musical key in Camelot notation (e.g. 8A, 11B)",
            "Energy level from 1 (calm) to 10 (intense)",
            "Track duration in minutes and seconds",
            "Spectral color profile (RED = bass, GREEN = mids, BLUE = highs)",
            "Metadata fields still missing for this track",
            "Primary genre detected by Mixed In Key",
            "Metadata completeness: complete or incomplete",
            "Click to preview the track",
            "Full file path on disk",
        ]
        for col, tip in enumerate(_HEADER_TOOLTIPS):
            header_item = self.tracks_table.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setToolTip(self.tr(tip))
        # Allow users to reorder columns by dragging headers.
        header.setSectionsMovable(True)
        # Stretch all columns by default so the table fills available width.
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Narrow data columns only take the space they need.
        for col in (2, 3, 4, 5, 6, 9, 10):  # BPM, Key, Energy, Duration, Color, Status, Preview
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.tracks_table.setAlternatingRowColors(True)
        self.tracks_table.setSelectionBehavior(self.tracks_table.SelectionBehavior.SelectRows)
        self.tracks_table.verticalHeader().setVisible(False)
        # Hide Path column by default — full paths are rarely useful at a glance.
        self.tracks_table.setColumnHidden(len(_COLUMNS) - 1, True)
        # Hide Missing column by default — useful on demand, but cramped during browsing.
        self.tracks_table.setColumnHidden(_MISSING_COLUMN, True)
        layout.addWidget(self.tracks_table)

        # Bottom row
        bottom = QHBoxLayout()
        self.settings_button = QPushButton(self.tr("⚙ Settings"))
        self.settings_button.setObjectName("secondaryAction")
        self.settings_button.setMaximumHeight(26)
        self.help_button = QPushButton(self.tr("What's this?"))
        self.help_button.setObjectName("secondaryAction")
        self.help_button.setMaximumHeight(26)
        self.tour_button = QPushButton(self.tr("Tour"))
        self.tour_button.setObjectName("secondaryAction")
        self.tour_button.setMaximumHeight(26)
        self.proceed_button = QPushButton(self.tr("Build Playlist →"))
        bottom.addWidget(self.settings_button)
        bottom.addWidget(self.help_button)
        bottom.addWidget(self.tour_button)
        bottom.addStretch()
        bottom.addWidget(self.proceed_button)
        layout.addLayout(bottom)

        self._setup_button_tooltips()
        self._setup_accessibility()
        self._setup_tab_order()

    def _setup_button_tooltips(self) -> None:
        """Explain every button so novice DJs understand each control (R1)."""
        tips = {
            self.folder_button: "Choose the music folder XfinAudio should scan",
            self.scan_button: "Read metadata (BPM, key, energy) from your tracks",
            self.cancel_button: "Stop the metadata scan currently in progress",
            self.missing_column_button: "Show or hide the column listing missing metadata",
            self.clear_filters_button: "Clear all active quick filters",
            self.settings_button: "Open scan and application settings",
            self.help_button: "Show a quick explanation of this screen",
            self.tour_button: "Walk through the full workflow step by step",
            self.proceed_button: "Move on to building a playlist from this library",
            self.complete_filter_button: "Show only tracks with complete metadata",
            self.incomplete_filter_button: "Show only tracks with missing metadata",
            self.missing_bpm_filter_button: "Show only tracks missing a BPM value",
            self.missing_key_filter_button: "Show only tracks missing a musical key",
            self.missing_energy_filter_button: "Show only tracks missing an energy level",
        }
        for button, tip in tips.items():
            button.setToolTip(self.tr(tip))

    def build_help_dialog(self) -> QMessageBox:
        """Return a 'What's this?' dialog describing the Library workflow (R3)."""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(self.tr("Library — What's this?"))
        dialog.setText(
            self.tr(
                "Choose a music folder, then scan metadata to load your tracks. "
                "Use search and quick filters to find songs, then click "
                "Build Playlist to continue."
            )
        )
        return dialog

    def tour_steps(self) -> list[str]:
        """Return the ordered workflow walkthrough shown by the Tour button (R4)."""
        return [
            self.tr("1. Choose a music folder with your tracks."),
            self.tr("2. Scan metadata to read BPM, key, and energy."),
            self.tr("3. Search or filter to find the songs you want."),
            self.tr("4. Click Build Playlist to start a recommendation."),
        ]

    def _show_tour(self) -> None:
        QMessageBox.information(self, self.tr("Workflow Tour"), "\n".join(self.tour_steps()))

    def _show_help(self) -> None:
        self.build_help_dialog().exec()

    def _setup_accessibility(self) -> None:
        """Set accessible names for screen readers."""
        self.folder_button.setAccessibleName(self.tr("Choose music folder"))
        self.scan_button.setAccessibleName(self.tr("Scan metadata"))
        self.cancel_button.setAccessibleName(self.tr("Cancel scan"))
        self.missing_column_button.setAccessibleName(self.tr("Show or hide missing metadata column"))
        self.search_input.setAccessibleName(self.tr("Search songs"))
        self.search_input.setAccessibleDescription(
            self.tr("Type to filter the track library by title, artist, BPM, key, or genre.")
        )
        self.tracks_table.setAccessibleName(self.tr("Library track list"))
        self.settings_button.setAccessibleName(self.tr("Open settings"))
        self.proceed_button.setAccessibleName(self.tr("Build playlist"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.folder_button, self.scan_button)
        self.setTabOrder(self.scan_button, self.cancel_button)
        self.setTabOrder(self.cancel_button, self.missing_column_button)
        self.setTabOrder(self.missing_column_button, self.search_input)
        self.setTabOrder(self.search_input, self.tracks_table)
        self.setTabOrder(self.tracks_table, self.settings_button)
        self.setTabOrder(self.settings_button, self.proceed_button)

    def _connect_signals(self) -> None:
        self.folder_button.clicked.connect(self.folder_change_requested)
        self.scan_button.clicked.connect(self.scan_requested)
        self.cancel_button.clicked.connect(self.cancel_scan_requested)
        self.missing_column_button.clicked.connect(self._toggle_missing_column)
        self.tracks_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.tracks_table.itemDoubleClicked.connect(self._on_track_double_clicked)
        self.tracks_table.cellClicked.connect(self._on_cell_clicked)
        self.search_input.textChanged.connect(self._on_search_changed)
        for button in self.quick_filter_buttons:
            button.clicked.connect(self._on_quick_filter_changed)
        self.clear_filters_button.clicked.connect(self._clear_quick_filters)
        self.settings_button.clicked.connect(self.settings_requested)
        self.help_button.clicked.connect(self._show_help)
        self.tour_button.clicked.connect(self._show_tour)
        self.tracks_table.horizontalHeader().sectionDoubleClicked.connect(self._on_header_double_clicked)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: LibraryViewModel, state: AppState, lightweight: bool = False) -> None:
        """Update all widgets from ViewModel data.

        Args:
            lightweight: If True, skip expensive table population and filtering
                        (used for non-visible tabs during state sync).
        """
        self._last_vm = vm
        self._last_state = state
        self.scan_button.setEnabled(vm.scan_button_enabled(state))
        self.cancel_button.setVisible(vm.cancel_button_visible(state))
        self.scan_settings_label.setText(vm.scan_settings_review_text(state))
        self.status_label.setText(vm.status_text(state))
        self._render_scan_progress(state)
        self.proceed_button.setEnabled(vm.can_proceed(state))
        self._render_empty_state(state)
        if lightweight:
            return
        rows = vm.tracks_for_display(state, self._current_library_filters())
        sort_column = self._sort_column
        if sort_column is not None:
            rows = sorted(
                rows,
                key=lambda r: _sort_key_for_column(r, sort_column),
                reverse=not self._sort_ascending,
            )
        self._populate_table(rows)
        self._apply_filter()
        self._apply_constraint_colors(state.excluded_paths, state.locked_paths)
        self._apply_playing_highlight()

    def _render_empty_state(self, state: AppState) -> None:
        if state.selected_folder is None:
            text = self.tr("🎵 No library yet — choose a music folder to get started.")
        elif not state.scanned_records:
            text = self.tr("📂 Folder selected — scan metadata to load your tracks.")
        else:
            text = ""
        self.empty_state_label.setText(text)
        self.empty_state_label.setVisible(bool(text))

    def _render_scan_progress(self, state: AppState) -> None:
        if not state.is_scanning:
            self.scan_progress_bar.setVisible(False)
            self.scan_progress_label.setVisible(False)
            self.scan_progress_label.setText("")
            return
        self.scan_progress_bar.setValue(progress_percent(state.scan_progress_count, state.scan_progress_total))
        self.scan_progress_label.setText(
            progress_status_text(state.scan_progress_count, state.scan_progress_total, state.scan_elapsed_seconds)
        )
        self.scan_progress_bar.setVisible(True)
        self.scan_progress_label.setVisible(True)

    def _populate_table(self, rows: list[TrackDisplayRow]) -> None:
        # Preserve selected paths so sorting does not lose selection.
        path_col = len(_COLUMNS) - 1
        selected_paths = {
            self.tracks_table.item(idx.row(), path_col).text()
            for idx in self.tracks_table.selectedIndexes()
            if self.tracks_table.item(idx.row(), path_col) is not None
        }

        self.tracks_table.blockSignals(True)
        try:
            self.tracks_table.setRowCount(0)
            for row_data in rows:
                row = self.tracks_table.rowCount()
                self.tracks_table.insertRow(row)
                preview_text = "⏸" if row_data.path == self._playing_path else "▶"
                values = [
                    row_data.title,
                    row_data.artist,
                    row_data.bpm,
                    row_data.musical_key,
                    row_data.energy,
                    row_data.duration,
                    row_data.spectral_color,
                    row_data.missing_fields,
                    row_data.genre,
                    row_data.metadata_status,
                    preview_text,
                    row_data.path,  # full path for lookup; display_path only for UI labels
                ]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setToolTip(value)
                    self.tracks_table.setItem(row, col, item)
        finally:
            self.tracks_table.blockSignals(False)

        # Restore selection after repopulation.
        for row in range(self.tracks_table.rowCount()):
            path_item = self.tracks_table.item(row, path_col)
            if path_item is not None and path_item.text() in selected_paths:
                self.tracks_table.selectRow(row)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_header_double_clicked(self, column: int) -> None:
        if self._sort_column == column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True
        header = self.tracks_table.horizontalHeader()
        from PySide6.QtCore import Qt

        header.setSortIndicator(
            column,
            Qt.SortOrder.AscendingOrder if self._sort_ascending else Qt.SortOrder.DescendingOrder,
        )
        if self._last_vm is not None and self._last_state is not None:
            self.render(self._last_vm, self._last_state)

    def _toggle_missing_column(self) -> None:
        self._missing_column_visible = not self._missing_column_visible
        self.tracks_table.setColumnHidden(_MISSING_COLUMN, not self._missing_column_visible)
        button_text = "Hide Missing" if self._missing_column_visible else "Show Missing"
        self.missing_column_button.setText(self.tr(button_text))

    def _on_search_changed(self, text: str) -> None:
        self._filter_query = text.strip().casefold()
        self._apply_filter()

    def _on_quick_filter_changed(self) -> None:
        sender = self.sender()
        status_buttons = (self.complete_filter_button, self.incomplete_filter_button)
        missing_buttons = (
            self.missing_bpm_filter_button,
            self.missing_key_filter_button,
            self.missing_energy_filter_button,
        )
        active_group = status_buttons if sender in status_buttons else missing_buttons
        if sender.isChecked():
            for button in active_group:
                if button is not sender:
                    button.setChecked(False)
        self._refresh_filter_state()

    def _clear_quick_filters(self) -> None:
        self.clear_quick_filters(emit_signal=True)

    def clear_quick_filters(self, *, emit_signal: bool) -> None:
        """Clear quick filters, optionally emitting undoable-action metadata."""
        active_labels = [button.text() for button in self.quick_filter_buttons if button.isChecked()]
        for button in self.quick_filter_buttons:
            button.setChecked(False)
        self._refresh_filter_state()
        if emit_signal and active_labels:
            self.filters_cleared.emit(active_labels)

    def restore_quick_filters(self, labels: list[str]) -> None:
        """Re-check the quick-filter buttons named in *labels* (undo support)."""
        wanted = set(labels)
        for button in self.quick_filter_buttons:
            button.setChecked(button.text() in wanted)
        self._refresh_filter_state()

    def _refresh_filter_state(self) -> None:
        active_count = sum(1 for button in self.quick_filter_buttons if button.isChecked())
        self.active_filter_count_label.setText(self.tr("{0} active").format(active_count))
        if self._last_vm is not None and self._last_state is not None:
            self.render(self._last_vm, self._last_state)

    def _current_library_filters(self) -> LibraryFilters:
        status_filter = "complete" if self.complete_filter_button.isChecked() else None
        if self.incomplete_filter_button.isChecked():
            status_filter = "incomplete"
        missing_filter = next(
            (
                field_name
                for button, field_name in (
                    (self.missing_bpm_filter_button, "bpm"),
                    (self.missing_key_filter_button, "camelot_key"),
                    (self.missing_energy_filter_button, "energy_level"),
                )
                if button.isChecked()
            ),
            None,
        )
        return LibraryFilters(status_filter=status_filter, missing_field_filter=missing_filter)

    def _apply_filter(self) -> None:
        query = self._filter_query
        # Search across Title, Artist, BPM, Key, Genre (cols 0-3, 8). Exclude path (col 11).
        _SEARCH_COLS = (0, 1, 2, 3, 8)
        for row in range(self.tracks_table.rowCount()):
            if not query:
                self.tracks_table.setRowHidden(row, False)
                continue
            match = any(query in (self.tracks_table.item(row, col) or _EMPTY).text().casefold() for col in _SEARCH_COLS)
            self.tracks_table.setRowHidden(row, not match)

    def _apply_constraint_colors(self, excluded: frozenset[str], locked: frozenset[str]) -> None:
        if not excluded and not locked:
            return
        _EXCLUDED_COLOR = QColor("#4a1a1a")
        _LOCKED_COLOR = QColor("#3a3010")
        col_count = self.tracks_table.columnCount()
        path_col = len(_COLUMNS) - 1  # Path is last column
        for row in range(self.tracks_table.rowCount()):
            path_item = self.tracks_table.item(row, path_col)
            if path_item is None:
                continue
            path = path_item.text()
            if path in excluded:
                color = _EXCLUDED_COLOR
            elif path in locked:
                color = _LOCKED_COLOR
            else:
                continue
            for col in range(col_count):
                item = self.tracks_table.item(row, col)
                if item is not None:
                    item.setBackground(color)

    def _on_track_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        path_col = len(_COLUMNS) - 1  # Path is last column
        path_item = self.tracks_table.item(row, path_col)
        if path_item is not None:
            self.track_play_requested.emit(path_item.text())

    def _on_cell_clicked(self, row: int, column: int) -> None:
        preview_col = _COLUMNS.index("Preview")
        if column != preview_col:
            return
        path_col = len(_COLUMNS) - 1
        path_item = self.tracks_table.item(row, path_col)
        if path_item is None:
            return
        path = path_item.text()
        if self._playing_path == path:
            self.pause_requested.emit()
        else:
            self.play_requested.emit(path)

    def set_playing_row(self, path: str | None) -> None:
        """Highlight *path* as the currently playing track, or None to clear."""
        self._playing_path = path
        if self._last_vm is not None and self._last_state is not None:
            self.render(self._last_vm, self._last_state)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Space toggles play/pause for the selected track."""
        if event.key() == Qt.Key.Key_Space and self.tracks_table.hasFocus():
            selected = self.tracks_table.selectedIndexes()
            if selected:
                row = selected[0].row()
                path_col = len(_COLUMNS) - 1
                path_item = self.tracks_table.item(row, path_col)
                if path_item is not None:
                    path = path_item.text()
                    if self._playing_path == path:
                        self.pause_requested.emit()
                    else:
                        self.play_requested.emit(path)
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_selection_changed(self) -> None:
        selected_rows = {idx.row() for idx in self.tracks_table.selectedIndexes()}
        self._paint_row_selection(selected_rows)
        paths: list[str] = []
        for row in selected_rows:
            path_item = self.tracks_table.item(row, len(_COLUMNS) - 1)
            if path_item is not None:
                paths.append(path_item.text())
        self.selection_changed.emit(paths)

    def _find_row_by_path(self, path: str) -> int | None:
        path_col = len(_COLUMNS) - 1
        for row in range(self.tracks_table.rowCount()):
            item = self.tracks_table.item(row, path_col)
            if item is not None and item.text() == path:
                return row
        return None

    def _apply_playing_highlight(self) -> None:
        if self._playing_path is None:
            return
        row = self._find_row_by_path(self._playing_path)
        if row is None:
            return
        col_count = self.tracks_table.columnCount()
        for col in range(col_count):
            item = self.tracks_table.item(row, col)
            if item is not None:
                item.setBackground(_ROW_COLOR_SELECTED)

    def _paint_row_selection(self, selected_rows: set[int]) -> None:
        playing_row = self._find_row_by_path(self._playing_path) if self._playing_path else None
        col_count = self.tracks_table.columnCount()
        for row in range(self.tracks_table.rowCount()):
            if row == playing_row or row in selected_rows:
                color = _ROW_COLOR_SELECTED
            else:
                color = _ROW_COLOR_ODD if row % 2 else _ROW_COLOR_EVEN
            for col in range(col_count):
                item = self.tracks_table.item(row, col)
                if item is not None:
                    item.setBackground(color)
