"""ExportScreen — thin QWidget that renders ExportViewModel data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.scan_service import progress_percent, progress_status_text

_TRACK_COLUMNS = ["#", "Title", "Artist", "BPM", "Key", "Energy"]

_HISTORY_COLUMNS = ["Time", "Strategy", "Tracks", "Serato Crate", "Readiness JSON", "Readiness CSV"]
_HISTORY_HEADER_TOOLTIPS = [
    "When this export was created",
    "Recommendation strategy used for this export",
    "Number of tracks in the exported playlist",
    "Path to the generated Serato crate file",
    "Path to the readiness report in JSON format",
    "Path to the readiness report in CSV format",
]


class ExportScreen(QWidget):
    """Displays export controls and history."""

    preview_requested = Signal()
    export_requested = Signal()
    readiness_export_requested = Signal()
    safe_folder_change_requested = Signal()
    back_requested = Signal()
    software_changed = Signal(str)
    tracks_reordered = Signal(list)
    track_removed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._track_paths: list[str] = []
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
        self.software_selector = QComboBox()
        for name in ["Serato", "Rekordbox", "Traktor", "VirtualDJ"]:
            self.software_selector.addItem(name)
        self.safe_folder_label = QLabel()
        self.safe_folder_button = QPushButton(self.tr("Choose Folder"))
        info_row.addWidget(self.variant_label)
        info_row.addWidget(self.software_selector)
        info_row.addStretch()
        info_row.addWidget(self.safe_folder_label)
        info_row.addWidget(self.safe_folder_button)
        layout.addLayout(info_row)

        # Export guidance label (set imperatively by main_window)
        self.export_guidance_label = QLabel(
            self.tr(
                "Review recommendations before exporting. "
                "Live Serato writes are not part of the verified release candidate; "
                "back up your library and verify any manual copy."
            )
        )
        self.export_guidance_label.setWordWrap(True)
        self.export_guidance_label.setMaximumHeight(32)
        layout.addWidget(self.export_guidance_label)

        # Safe export folder label (set imperatively by main_window)
        self.safe_export_folder_label = QLabel(self.tr("No safe export folder selected"))
        self.safe_export_folder_label.setMaximumHeight(24)
        layout.addWidget(self.safe_export_folder_label)

        # Playlist summary
        self.playlist_info_label = QLabel("—")
        self.playlist_info_label.setObjectName("statusLabel")
        self.playlist_info_label.setMaximumHeight(24)
        layout.addWidget(self.playlist_info_label)

        # The set itself, editable. Before this the screen showed only the
        # summary above, and the spare height went to it because the history
        # table below is hidden until the first export -- a window-tall empty
        # panel where the tracks should have been.
        self.tracks_table = QTableWidget(0, len(_TRACK_COLUMNS))
        self.tracks_table.setHorizontalHeaderLabels([self.tr(c) for c in _TRACK_COLUMNS])
        tracks_header = self.tracks_table.horizontalHeader()
        # Free width goes to Title and Artist; the rest hold short fixed values.
        tracks_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for name in ("Title", "Artist"):
            tracks_header.setSectionResizeMode(_TRACK_COLUMNS.index(name), QHeaderView.ResizeMode.Stretch)
        self.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tracks_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tracks_table.verticalHeader().setVisible(False)
        self.tracks_table.setAlternatingRowColors(True)
        self.tracks_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tracks_table, 1)

        # Edit controls
        edit_row = QHBoxLayout()
        self.move_up_button = QPushButton(self.tr("↑ Move Up"))
        self.move_up_button.setObjectName("secondaryAction")
        self.move_up_button.setMaximumHeight(26)
        self.move_down_button = QPushButton(self.tr("↓ Move Down"))
        self.move_down_button.setObjectName("secondaryAction")
        self.move_down_button.setMaximumHeight(26)
        self.remove_button = QPushButton(self.tr("Remove"))
        self.remove_button.setObjectName("secondaryAction")
        self.remove_button.setMaximumHeight(26)
        for button in (self.move_up_button, self.move_down_button, self.remove_button):
            button.setEnabled(False)
            edit_row.addWidget(button)
        edit_row.addStretch()
        layout.addLayout(edit_row)

        # Empty-state / guidance label
        self.empty_state_label = QLabel()
        self.empty_state_label.setWordWrap(True)
        self.empty_state_label.setMaximumHeight(32)
        layout.addWidget(self.empty_state_label)

        # Action buttons
        actions = QHBoxLayout()
        self.preview_button = QPushButton(self.tr("Preview Serato Export"))
        self.preview_button.setObjectName("secondaryAction")
        self.preview_button.setMaximumHeight(26)
        self.export_button = QPushButton(self.tr("Export to Serato"))
        self.export_button.setObjectName("seratoExportButton")
        self.export_button.setMinimumHeight(36)
        self.export_button.setEnabled(False)
        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setRange(0, 100)
        self.export_progress_bar.setTextVisible(False)
        self.export_progress_bar.setVisible(False)
        self.export_progress_label = QLabel("")
        self.export_progress_label.setVisible(False)
        self.export_readiness_button = QPushButton(self.tr("Export Readiness Report"))
        self.export_readiness_button.setEnabled(False)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.export_progress_bar)
        actions.addWidget(self.export_progress_label)
        actions.addWidget(self.export_readiness_button)
        actions.addStretch()
        layout.addLayout(actions)

        # Section divider between controls and history table
        self.section_divider = QFrame()
        self.section_divider.setObjectName("sectionDivider")
        self.section_divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.section_divider)

        # Export history table (hidden until first export) — absorbs all spare vertical space.
        self.history_table = QTableWidget(0, len(_HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels([self.tr(c) for c in _HISTORY_COLUMNS])
        for col, tip in enumerate(_HISTORY_HEADER_TOOLTIPS):
            header_item = self.history_table.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setToolTip(self.tr(tip))
        history_header = self.history_table.horizontalHeader()
        # Free width goes to the three path columns; Time, Strategy and Tracks
        # hold a timestamp, a name and a count.
        history_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for name in ("Time", "Strategy", "Tracks"):
            history_header.setSectionResizeMode(_HISTORY_COLUMNS.index(name), QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.history_table.setMinimumHeight(200)
        self.history_table.setVisible(False)
        layout.addWidget(self.history_table, 1)

        # Navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton(self.tr("← Review"))
        self.back_button.setObjectName("secondaryAction")
        self.back_button.setMaximumHeight(26)
        nav.addWidget(self.back_button)
        nav.addStretch()
        layout.addLayout(nav)

        self._setup_button_tooltips()
        self._setup_accessibility()
        self._setup_tab_order()

    def _setup_button_tooltips(self) -> None:
        """Explain every button so users understand each control (R1)."""
        tips = {
            self.safe_folder_button: "Choose the safe folder where exports are written",
            self.preview_button: "Preview the export without writing any files",
            self.export_button: "Write the playlist to your DJ software's crate",
            self.export_readiness_button: "Export the readiness report as JSON and CSV",
            self.move_up_button: "Move the selected track one place earlier in the set",
            self.move_down_button: "Move the selected track one place later in the set",
            self.remove_button: "Drop the selected track from the set before exporting",
            self.back_button: "Return to the Review screen",
        }
        for button, tip in tips.items():
            button.setToolTip(self.tr(tip))

    def _setup_accessibility(self) -> None:
        """Set accessible names for screen readers."""
        self.variant_label.setAccessibleName(self.tr("Applied variant"))
        self.software_selector.setAccessibleName(self.tr("DJ software selector"))
        self.safe_folder_label.setAccessibleName(self.tr("Safe export folder"))
        self.safe_folder_button.setAccessibleName(self.tr("Choose safe export folder"))
        self.export_guidance_label.setAccessibleName(self.tr("Export guidance"))
        self.preview_button.setAccessibleName(self.tr("Preview export"))
        self.export_button.setAccessibleName(self.tr("Export recommendation"))
        self.export_readiness_button.setAccessibleName(self.tr("Export readiness report"))
        self.tracks_table.setAccessibleName(self.tr("Tracks to export"))
        self.move_up_button.setAccessibleName(self.tr("Move track up"))
        self.move_down_button.setAccessibleName(self.tr("Move track down"))
        self.remove_button.setAccessibleName(self.tr("Remove track from the set"))
        self.history_table.setAccessibleName(self.tr("Export history"))
        self.back_button.setAccessibleName(self.tr("Back to review"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.software_selector, self.safe_folder_button)
        self.setTabOrder(self.safe_folder_button, self.tracks_table)
        self.setTabOrder(self.tracks_table, self.move_up_button)
        self.setTabOrder(self.move_up_button, self.move_down_button)
        self.setTabOrder(self.move_down_button, self.remove_button)
        self.setTabOrder(self.remove_button, self.preview_button)
        self.setTabOrder(self.preview_button, self.export_button)
        self.setTabOrder(self.export_button, self.export_readiness_button)
        self.setTabOrder(self.export_readiness_button, self.history_table)
        self.setTabOrder(self.history_table, self.back_button)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.preview_button.clicked.connect(self.preview_requested)
        self.export_button.clicked.connect(self.export_requested)
        self.export_readiness_button.clicked.connect(self.readiness_export_requested)
        self.safe_folder_button.clicked.connect(self.safe_folder_change_requested)
        self.software_selector.currentTextChanged.connect(self._on_software_changed)
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))
        self.remove_button.clicked.connect(self._remove_selected)
        self.tracks_table.itemSelectionChanged.connect(self._sync_edit_buttons)

    # ------------------------------------------------------------------
    # Track list editing
    # ------------------------------------------------------------------

    def visible_track_paths(self) -> list[str]:
        """Return the paths in the order the table currently shows them."""
        return list(self._track_paths)

    def _selected_row(self) -> int:
        rows = self.tracks_table.selectionModel().selectedRows() if self.tracks_table.selectionModel() else []
        return rows[0].row() if rows else -1

    def _sync_edit_buttons(self) -> None:
        row = self._selected_row()
        selected = 0 <= row < len(self._track_paths)
        # No wraparound: one click never sends the first track to the bottom.
        self.move_up_button.setEnabled(selected and row > 0)
        self.move_down_button.setEnabled(selected and row < len(self._track_paths) - 1)
        self.remove_button.setEnabled(selected)

    def _move_selected(self, offset: int) -> None:
        row = self._selected_row()
        target = row + offset
        if not (0 <= row < len(self._track_paths) and 0 <= target < len(self._track_paths)):
            return
        self._track_paths[row], self._track_paths[target] = self._track_paths[target], self._track_paths[row]
        self._reorder_rows(row, target)
        self.tracks_table.selectRow(target)
        self.tracks_reordered.emit(list(self._track_paths))

    def _reorder_rows(self, row: int, target: int) -> None:
        """Swap two rendered rows in place.

        Repopulating from the recommendation is not an option here: the state
        update travels through the controller, so the table would still hold
        the pre-move order when this returns and the row would visibly snap
        back.
        """
        for column in range(self.tracks_table.columnCount()):
            left = self.tracks_table.takeItem(row, column)
            right = self.tracks_table.takeItem(target, column)
            self.tracks_table.setItem(row, column, right)
            self.tracks_table.setItem(target, column, left)
        self._renumber_rows()

    def _renumber_rows(self) -> None:
        for index in range(self.tracks_table.rowCount()):
            item = self.tracks_table.item(index, 0)
            if item is not None:
                item.setText(str(index + 1))

    def _remove_selected(self) -> None:
        row = self._selected_row()
        if not 0 <= row < len(self._track_paths):
            return
        path = self._track_paths.pop(row)
        self.tracks_table.removeRow(row)
        self._renumber_rows()
        self._sync_edit_buttons()
        self.track_removed.emit(path)

    def _populate_tracks_table(self, state: AppState) -> None:
        recommendation = state.last_recommendation
        tracks = list(recommendation.ordered_tracks) if recommendation is not None else []
        paths = [track.path for track in tracks]
        if paths == self._track_paths:
            # The controller echoes our own edit back on the next render; leave
            # the rendered rows and the user's selection alone.
            return
        self._track_paths = paths
        self.tracks_table.setRowCount(0)
        for index, track in enumerate(tracks):
            self.tracks_table.insertRow(index)
            for column, text in enumerate(
                (
                    str(index + 1),
                    track.title or Path(track.path).name,
                    track.artist or "—",
                    "—" if track.bpm is None else f"{track.bpm:g}",
                    track.camelot_key or "—",
                    "—" if track.energy_level is None else f"E{track.energy_level}",
                )
            ):
                item = QTableWidgetItem(text)
                item.setToolTip(track.path)
                self.tracks_table.setItem(index, column, item)
        self._sync_edit_buttons()

    def connect_signals(self, window: Any) -> None:
        self.preview_requested.connect(window.preview_export)
        self.export_requested.connect(window.export_recommendation)
        self.readiness_export_requested.connect(lambda: window.export_dj_readiness_report())
        self.safe_folder_change_requested.connect(window._export_actions.choose_safe_export_folder)
        self.back_requested.connect(lambda: window.workflow_tabs.setCurrentIndex(2))
        self.tracks_reordered.connect(lambda paths: self._apply_track_order(window, paths))
        self.track_removed.connect(lambda path: self._apply_track_removal(window, path))

    @staticmethod
    def _spectral_cohesion(window: Any) -> float:
        """Read the cohesion the set was built with, so a rescore matches it."""
        build_screen = getattr(window, "_build_screen", None)
        if build_screen is None:
            return 0.0
        return build_screen.spectral_cohesion_value() / 100.0

    def _apply_track_order(self, window: Any, paths: list[str]) -> None:
        from xfinaudio.desktop.app_state_transitions import apply_export_track_order

        window._replace_app_state(
            apply_export_track_order(window._state, paths, spectral_cohesion=self._spectral_cohesion(window))
        )

    def _apply_track_removal(self, window: Any, path: str) -> None:
        from xfinaudio.desktop.app_state_transitions import apply_export_track_removal

        window._replace_app_state(
            apply_export_track_removal(window._state, path, spectral_cohesion=self._spectral_cohesion(window))
        )

    def _on_software_changed(self, name: str) -> None:
        """Update button labels and emit software selection change."""
        self.preview_button.setText(self.tr(f"Preview {name} Export"))
        self.export_button.setText(self.tr(f"Export to {name}"))
        self.software_changed.emit(name)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: ExportViewModel, state: AppState, lightweight: bool = False) -> None:
        """Update all widgets from ViewModel data.

        Args:
            lightweight: Unused for ExportScreen (render is already lightweight
                        - no table population). Kept for API consistency.
        """
        self.variant_label.setText(vm.applied_variant_label(state))
        self.safe_folder_label.setText(vm.safe_folder_label(state))
        self.playlist_info_label.setText(vm.preview_text(state) or "—")
        self._populate_tracks_table(state)
        self._render_export_progress(state)
        self.export_button.setEnabled(vm.export_enabled(state))
        self.export_readiness_button.setEnabled(vm.export_readiness_enabled(state))
        # history_table is populated imperatively by _render_serato_export_history
        empty = vm.empty_state_text(state)
        if empty:
            self.empty_state_label.setText(empty)
            self.empty_state_label.setVisible(True)
        else:
            self.empty_state_label.setText(f"{vm.preview_explanation_text()} {vm.destination_text()}")
            self.empty_state_label.setVisible(True)

    def _render_export_progress(self, state: AppState) -> None:
        if not state.is_exporting:
            self.export_progress_bar.setVisible(False)
            self.export_progress_label.setVisible(False)
            self.export_progress_label.setText("")
            return
        self.export_progress_bar.setValue(progress_percent(state.export_progress_count, state.export_progress_total))
        self.export_progress_label.setText(
            progress_status_text(state.export_progress_count, state.export_progress_total, state.export_elapsed_seconds)
        )
        self.export_progress_bar.setVisible(True)
        self.export_progress_label.setVisible(True)
