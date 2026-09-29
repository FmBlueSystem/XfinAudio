"""Rendering and table interaction behavior for LibraryScreen."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QCoreApplication, QItemSelection, QItemSelectionModel, QItemSelectionRange, Qt
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import QTableWidgetItem

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus, is_complete_measurement
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_columns import COLUMNS, column_index, ordered_cells
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
_ROW_COLOR_EVEN = QColor("#0f1a24")
_ROW_COLOR_ODD = QColor("#13202c")
_ROW_COLOR_SELECTED = QColor("#6a55f0")
_COLUMNS = list(COLUMNS)
_MISSING_COLUMN = column_index("Missing")
_TITLE_COLUMN = _COLUMNS.index("Title")
_ARTIST_COLUMN = _COLUMNS.index("Artist")
_STATUS_COLUMN = _COLUMNS.index("Status")
_PREVIEW_COLUMN = _COLUMNS.index("Preview")


def _library_rows_signature(rows: list[TrackDisplayRow]) -> tuple:
    """Return a comparable signature of the library rows shown in the table.

    render() runs on every state sync for the visible Library tab, and
    rebuilding the table would reset the DJ's selection, currentRow, and scroll
    position even when the rows are identical. The signature covers every cell
    _populate_table writes (tooltips mirror cell text) in row order, so a sort
    or filter change also invalidates it. The Preview cell depends on the
    playing path, which is tracked separately in the render extras.
    """
    return tuple(
        (
            row.path,
            row.title,
            row.artist,
            row.bpm,
            row.musical_key,
            row.energy,
            row.lufs,
            row.duration,
            row.missing_fields,
            row.genre,
            row.metadata_status,
            row.spectral_color,
        )
        for row in rows
    )


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
        self.rescan_button.setVisible(vm.rescan_button_visible(state))
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
        rows_signature = _library_rows_signature(rows)
        # Excluded/locked sets and the playing path are painted after populate,
        # so they must also gate the rebuild: skipping populate while they
        # changed would leave stale constraint colors behind.
        extras = (
            tuple(sorted(state.excluded_paths)),
            tuple(sorted(state.locked_paths)),
            self._playing_path,
        )
        # Skip the destructive rebuild when the rendered content is identical;
        # the same-rows path must keep the DJ's selection, currentRow, and
        # scroll position untouched.
        if (
            rows_signature != self._last_rows_signature
            or extras != self._last_render_extras
            or self.tracks_table.rowCount() != len(rows)
        ):
            self._populate_table(rows)
        self._last_rows_signature = rows_signature
        self._last_render_extras = extras
        self._apply_search_and_duplicate_filters()
        self._apply_constraint_colors(state.excluded_paths, state.locked_paths)
        self._apply_playing_highlight()

    def invalidate_library_render_cache(self) -> None:
        """Drop the cached rows signature so the next render rebuilds the table.

        Direct writes to ``tracks_table`` that bypass ``_populate_table`` (the
        controller repopulating the library after a scan or a saved-library
        restore) leave the cached signature describing rows that are no longer
        on screen. Without this, a later render of identical rows would skip
        the rebuild and keep the direct-write row order under an active sort,
        or a default Preview cell on the playing row.
        """
        self._last_rows_signature = None
        self._last_render_extras = None

    def _render_empty_state(self, state: AppState) -> None:
        # Records first: a library restored from the database has tracks but no
        # selected folder, and checking the folder alone announced "No library
        # yet" above thousands of listed tracks.
        if state.scanned_records:
            text = ""
        elif state.selected_folder is None:
            text = self.tr("🎵 No library yet — choose a music folder to get started.")
        else:
            text = self.tr("📂 Folder selected — scan metadata to load your tracks.")
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
            self.scan_progress_bar.setValue(progress_percent(state.spectral_progress_count, state.spectral_total_count))
            self.scan_progress_label.setText(
                self.tr("Analyzing colors {0:,}/{1:,}").format(
                    state.spectral_progress_count, state.spectral_total_count
                )
            )
            self.scan_progress_bar.setVisible(True)
            self.scan_progress_label.setVisible(True)
            return
        if state.is_completing_loudness and state.loudness_total_count > 0:
            self.scan_progress_bar.setValue(progress_percent(state.loudness_progress_count, state.loudness_total_count))
            self.scan_progress_label.setText(
                QCoreApplication.translate("LibraryScreen", "Analyzing loudness {0:,}/{1:,}").format(
                    state.loudness_progress_count, state.loudness_total_count
                )
            )
            self.scan_progress_bar.setVisible(True)
            self.scan_progress_label.setVisible(True)
            return
        self.scan_progress_bar.setVisible(False)
        self.scan_progress_label.setVisible(False)
        self.scan_progress_label.setText("")

    def set_loudness_details(self, profile: LoudnessProfile | None, *, visible: bool) -> None:
        """Render the selected track's loudness summary and true-peak status."""
        self.loudness_detail_pane.setVisible(visible)
        if not visible:
            self.loudness_detail_label.setText("")
            self.true_peak_badge.setText("")
            self.true_peak_badge.setVisible(False)
            return
        self.true_peak_badge.setText("")
        self.true_peak_badge.setVisible(False)
        if profile is None:
            self.loudness_detail_label.setText(QCoreApplication.translate("LibraryScreen", "Loudness: not measured"))
            return
        if profile.status is LoudnessStatus.TOO_SHORT:
            if profile.lufs_integrated is None:
                self.loudness_detail_label.setText(
                    QCoreApplication.translate("LibraryScreen", "Loudness: unavailable (too short)")
                )
            else:
                self.loudness_detail_label.setText(
                    QCoreApplication.translate(
                        "LibraryScreen", "LUFS: {0:.1f} · LRA: unavailable · True peak: unavailable (too short)"
                    ).format(profile.lufs_integrated)
                )
            return
        if not is_complete_measurement(profile):
            if profile.status is LoudnessStatus.UNMEASURABLE:
                text = QCoreApplication.translate("LibraryScreen", "Loudness: unmeasurable")
            elif profile.status is LoudnessStatus.TRANSIENT_FAILURE:
                text = QCoreApplication.translate("LibraryScreen", "Loudness: temporarily unavailable")
            elif profile.status is LoudnessStatus.UNSUPPORTED:
                text = QCoreApplication.translate("LibraryScreen", "Loudness: unsupported")
            else:
                text = QCoreApplication.translate("LibraryScreen", "Loudness: incomplete measurement")
            self.loudness_detail_label.setText(text)
            return
        # is_complete_measurement guarantees these three, but only at runtime.
        assert profile.lufs_integrated is not None
        assert profile.loudness_range_lra is not None
        assert profile.true_peak_dbtp is not None
        self.loudness_detail_label.setText(
            QCoreApplication.translate(
                "LibraryScreen", "LUFS: {0:.1f} · LRA: {1:.1f} · True peak: {2:.1f} dBTP"
            ).format(profile.lufs_integrated, profile.loudness_range_lra, profile.true_peak_dbtp)
        )
        if profile.true_peak_dbtp >= 0.0:
            badge = QCoreApplication.translate("LibraryScreen", "True peak clipping")
        elif profile.true_peak_dbtp > -1.0:
            badge = QCoreApplication.translate("LibraryScreen", "True peak warning")
        else:
            badge = ""
        self.true_peak_badge.setText(badge)
        self.true_peak_badge.setVisible(bool(badge))

    def _populate_table(self, rows: list[TrackDisplayRow]) -> None:
        """Rebuild the tracks table and restore the DJ's view state.

        The rebuild resets selection, currentRow, and scroll position, so all
        three are captured before and restored afterwards. Selection is
        restored by path (not row position) so a reordered library keeps the
        same tracks selected.
        """
        # Preserve selected paths so sorting does not lose selection.
        path_col = len(_COLUMNS) - 1
        selected_paths = {
            self.tracks_table.item(idx.row(), path_col).text()
            for idx in self.tracks_table.selectedIndexes()
            if self.tracks_table.item(idx.row(), path_col) is not None
        }
        current_path: str | None = None
        current_row = self.tracks_table.currentRow()
        if 0 <= current_row < self.tracks_table.rowCount():
            item = self.tracks_table.item(current_row, path_col)
            if item is not None:
                current_path = item.text()
        v_scroll = self.tracks_table.verticalScrollBar().value()
        h_scroll = self.tracks_table.horizontalScrollBar().value()

        self.tracks_table.blockSignals(True)
        try:
            self.tracks_table.setRowCount(0)
            for row_data in rows:
                row = self.tracks_table.rowCount()
                self.tracks_table.insertRow(row)
                preview_text = "⏸" if row_data.path == self._playing_path else "▶"
                values = ordered_cells(
                    {
                        "Title": row_data.title,
                        "Artist": row_data.artist,
                        "BPM": row_data.bpm,
                        "Key": row_data.musical_key,
                        "Energy": row_data.energy,
                        "LUFS": row_data.lufs,
                        "Duration": row_data.duration,
                        "Color": row_data.spectral_color,
                        "Missing": row_data.missing_fields,
                        "Genre": row_data.genre,
                        "Status": row_data.metadata_status,
                        "Preview": preview_text,
                        # full path for lookup; display_path only for UI labels
                        "Path": row_data.path,
                    }
                )
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setToolTip(value)
                    self.tracks_table.setItem(row, col, item)
        finally:
            self.tracks_table.blockSignals(False)

        self._restore_selection_and_scroll(selected_paths, current_path, v_scroll, h_scroll, path_col)
        self._last_rows_signature = _library_rows_signature(rows)

    def _restore_selection_and_scroll(
        self,
        selected_paths: set[str],
        current_path: str | None,
        v_scroll: int,
        h_scroll: int,
        path_col: int,
    ) -> None:
        """Re-select previously selected paths and restore scroll after a rebuild.

        All matched rows are re-selected in one QItemSelection block: the old
        per-row selectRow() loop replaced the previous selection on every call,
        collapsing a multi-row selection to its last match. setCurrentCell runs
        BEFORE the selection is applied — it can clear a freshly applied
        selection (the same pitfall ReviewScreen documents) — and scroll is
        restored last because setCurrentCell scrolls the current cell into
        view. The table's ExtendedSelection + SelectRows configuration is
        preserved: full-row ranges with a plain Select flag never change it.
        """
        matched_rows: list[int] = []
        restored_current_row: int | None = None
        for row in range(self.tracks_table.rowCount()):
            path_item = self.tracks_table.item(row, path_col)
            if path_item is None or path_item.text() not in selected_paths:
                continue
            matched_rows.append(row)
            if path_item.text() == current_path:
                restored_current_row = row
        if restored_current_row is None:
            restored_current_row = matched_rows[0] if matched_rows else None
        if restored_current_row is not None:
            self.tracks_table.setCurrentCell(restored_current_row, 0)
        self.tracks_table.clearSelection()
        if matched_rows:
            model = self.tracks_table.model()
            last_col = self.tracks_table.columnCount() - 1
            selection = QItemSelection()
            for row in matched_rows:
                selection.append(QItemSelectionRange(model.index(row, 0), model.index(row, last_col)))
            self.tracks_table.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.Select)
        # Restore scroll offsets last; Qt clamps out-of-range values, which is
        # correct when the new row count no longer scrolls that far.
        self.tracks_table.verticalScrollBar().setValue(v_scroll)
        self.tracks_table.horizontalScrollBar().setValue(h_scroll)

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
            # Surface guidance instead of failing silently: the Preview click
            # looks dead otherwise when the row carries no playable path.
            self.preview_without_path_requested.emit()
            return
        path = path_item.text()
        if self._playing_path == path:
            self.pause_requested.emit()
        else:
            self.play_requested.emit(path)

    def set_playing_row(self, path: str | None) -> None:
        """Highlight *path* as the currently playing track, or None to clear.

        WHY in-place: a play/pause toggle only changes the Preview cell text of
        the previous and new playing rows plus their background colors. When
        the table already shows the last-populated rows unchanged, a full
        render() would rebuild the table — resetting selection, currentRow, and
        scroll — for zero content change, so the two affected rows are updated
        in place instead, mirroring render()'s paint order (base colors,
        constraint colors, then the playing highlight). The full rebuild is
        still required when the records actually changed.
        """
        previous = self._playing_path
        self._playing_path = path
        if previous == path:
            return
        rows_current = (
            self._last_rows_signature is not None and len(self._last_rows_signature) == self.tracks_table.rowCount()
        )
        if not rows_current:
            if self._last_vm is not None and self._last_state is not None:
                self.render(self._last_vm, self._last_state)
            return
        for affected_path in (previous, path):
            if affected_path is None:
                continue
            row = self._find_row_by_path(affected_path)
            if row is None:
                continue
            item = self.tracks_table.item(row, _PREVIEW_COLUMN)
            if item is not None:
                item.setText("⏸" if affected_path == path else "▶")
            self._paint_row_base_backgrounds(row)
        if self._last_state is not None:
            self._apply_constraint_colors(self._last_state.excluded_paths, self._last_state.locked_paths)
        self._apply_playing_highlight()
        if self._last_render_extras is not None:
            # The playing path is the last extra; refresh it so the next
            # same-rows render keeps skipping the rebuild.
            self._last_render_extras = (*self._last_render_extras[:2], path)

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

    def _paint_row_base_backgrounds(self, row: int) -> None:
        """Repaint one row with its base selection/zebra color.

        Used by the in-place play-state update: a full _paint_row_selection
        pass would wipe constraint colors on unrelated rows, so only the
        affected row is reset here and render()'s paint order is mirrored by
        the caller (constraint colors, then the playing highlight).
        """
        selected_rows = {idx.row() for idx in self.tracks_table.selectedIndexes()}
        playing_row = self._find_row_by_path(self._playing_path) if self._playing_path else None
        if row == playing_row or row in selected_rows:
            color = _ROW_COLOR_SELECTED
        else:
            color = _ROW_COLOR_ODD if row % 2 else _ROW_COLOR_EVEN
        for col in range(self.tracks_table.columnCount()):
            item = self.tracks_table.item(row, col)
            if item is not None:
                item.setBackground(color)
