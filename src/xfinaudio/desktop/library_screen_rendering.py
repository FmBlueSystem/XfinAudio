"""Rendering and table interaction behavior for LibraryScreen."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import QTableWidgetItem

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_filter import _RowInfo, suppressed_duplicate_paths
from xfinaudio.desktop.library_filter_state import library_filters_from_flags, row_matches_query
from xfinaudio.desktop.library_table_presenter import sort_rows_for_column
from xfinaudio.desktop.library_view_model import (
    _DASH,
    MISSING_FIELDS_SEPARATOR,
    LibraryFilters,
    LibraryViewModel,
    TrackDisplayRow,
)
from xfinaudio.desktop.scan_service import progress_percent, progress_status_text

_EMPTY = QTableWidgetItem("")
_ROW_COLOR_EVEN = QColor("#101820")
_ROW_COLOR_ODD = QColor("#14202a")
_ROW_COLOR_SELECTED = QColor("#0078b4")
_MISSING_COLUMN = 7
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
_TITLE_COLUMN = _COLUMNS.index("Title")
_ARTIST_COLUMN = _COLUMNS.index("Artist")
_STATUS_COLUMN = _COLUMNS.index("Status")


class LibraryScreenRenderingMixin:
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
            rows = sort_rows_for_column(rows, sort_column, ascending=self._sort_ascending)
        self._populate_table(rows)
        self._apply_search_and_duplicate_filters()
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
        if state.is_scanning:
            self.scan_progress_bar.setValue(progress_percent(state.scan_progress_count, state.scan_progress_total))
            self.scan_progress_label.setText(
                progress_status_text(state.scan_progress_count, state.scan_progress_total, state.scan_elapsed_seconds)
            )
            self.scan_progress_bar.setVisible(True)
            self.scan_progress_label.setVisible(True)
            return
        if state.is_completing_spectral and state.spectral_total_count > 0:
            self.scan_progress_bar.setValue(
                progress_percent(state.spectral_progress_count, state.spectral_total_count)
            )
            self.scan_progress_label.setText(
                self.tr("Analyzing colors {0:,}/{1:,}").format(
                    state.spectral_progress_count, state.spectral_total_count
                )
            )
            self.scan_progress_bar.setVisible(True)
            self.scan_progress_label.setVisible(True)
            return
        self.scan_progress_bar.setVisible(False)
        self.scan_progress_label.setVisible(False)
        self.scan_progress_label.setText("")

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
        self._apply_search_and_duplicate_filters()

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

    def _all_filter_buttons(self) -> tuple[Any, ...]:
        # Includes hide_duplicates_button so Clear Filters, undo-restore, and the
        # active-count sum stay consistent, even though it is excluded from the
        # mutual-exclusion tuple `quick_filter_buttons`.
        return (*self.quick_filter_buttons, self.hide_duplicates_button)

    def clear_quick_filters(self, *, emit_signal: bool) -> None:
        """Clear quick filters, optionally emitting undoable-action metadata."""
        buttons = self._all_filter_buttons()
        active_labels = [button.text() for button in buttons if button.isChecked()]
        for button in buttons:
            button.setChecked(False)
        self._refresh_filter_state()
        if emit_signal and active_labels:
            self.filters_cleared.emit(active_labels)

    def restore_quick_filters(self, labels: list[str]) -> None:
        """Re-check the quick-filter buttons named in *labels* (undo support)."""
        wanted = set(labels)
        for button in self._all_filter_buttons():
            button.setChecked(button.text() in wanted)
        self._refresh_filter_state()

    def _refresh_filter_state(self) -> None:
        active_count = sum(1 for button in self._all_filter_buttons() if button.isChecked())
        self.active_filter_count_label.setText(self.tr("{0} active").format(active_count))
        if self._last_vm is not None and self._last_state is not None:
            self.render(self._last_vm, self._last_state)

    def _current_library_filters(self) -> LibraryFilters:
        return library_filters_from_flags(
            complete=self.complete_filter_button.isChecked(),
            incomplete=self.incomplete_filter_button.isChecked(),
            missing_bpm=self.missing_bpm_filter_button.isChecked(),
            missing_key=self.missing_key_filter_button.isChecked(),
            missing_energy=self.missing_energy_filter_button.isChecked(),
        )

    def _apply_filter(self) -> None:
        query = self._filter_query
        # Search across Title, Artist, BPM, Key, Genre (cols 0-3, 8). Exclude path (col 11).
        _SEARCH_COLS = (0, 1, 2, 3, 8)
        for row in range(self.tracks_table.rowCount()):
            if not query:
                self.tracks_table.setRowHidden(row, False)
                continue
            values = tuple((self.tracks_table.item(row, col) or _EMPTY).text() for col in _SEARCH_COLS)
            match = row_matches_query(values, query)
            self.tracks_table.setRowHidden(row, not match)

    def _apply_duplicate_filter(self) -> None:
        """Hide all but one representative row per near-duplicate group (display-only).

        Only considers rows that already survived `_apply_filter` (i.e. currently
        visible), so this can never permanently hide a row a search query would
        otherwise match. No-ops entirely — hides nothing, unhides nothing — when
        the toggle is off.
        """
        if not self.hide_duplicates_button.isChecked():
            self.duplicate_count_label.setText("")
            return
        path_col = len(_COLUMNS) - 1
        rows: list[_RowInfo] = []
        for row in range(self.tracks_table.rowCount()):
            if self.tracks_table.isRowHidden(row):
                continue
            title = (self.tracks_table.item(row, _TITLE_COLUMN) or _EMPTY).text()
            artist = (self.tracks_table.item(row, _ARTIST_COLUMN) or _EMPTY).text()
            status = (self.tracks_table.item(row, _STATUS_COLUMN) or _EMPTY).text()
            missing_text = (self.tracks_table.item(row, _MISSING_COLUMN) or _EMPTY).text()
            missing_field_count = 0 if missing_text == _DASH else len(missing_text.split(MISSING_FIELDS_SEPARATOR))
            path = (self.tracks_table.item(row, path_col) or _EMPTY).text()
            rows.append(
                _RowInfo(
                    title=title,
                    artist=artist,
                    status=status,
                    missing_field_count=missing_field_count,
                    path=path,
                )
            )
        suppressed = suppressed_duplicate_paths(rows)
        for row in range(self.tracks_table.rowCount()):
            if self.tracks_table.isRowHidden(row):
                continue
            path_item = self.tracks_table.item(row, path_col)
            if path_item is not None and path_item.text() in suppressed:
                self.tracks_table.setRowHidden(row, True)
        if not suppressed:
            # Distinct from the toggle-off empty string, so the user can tell
            # "inactive" apart from "active, nothing to hide right now".
            self.duplicate_count_label.setText(self.tr("No duplicates found"))
        elif len(suppressed) == 1:
            self.duplicate_count_label.setText(self.tr("1 duplicate hidden"))
        else:
            self.duplicate_count_label.setText(self.tr("{0} duplicates hidden").format(len(suppressed)))

    def _apply_search_and_duplicate_filters(self) -> None:
        """Run search then duplicate-suppression, always in this order, so the two
        passes can never run out of sync with each other."""
        self._apply_filter()
        self._apply_duplicate_filter()

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
