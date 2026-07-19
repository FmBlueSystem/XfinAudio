"""LibraryScreen — thin QWidget that renders LibraryViewModel data."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMessageBox,
    QTableWidgetItem,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_screen_builder import build_library_screen_ui
from xfinaudio.desktop.library_screen_rendering import LibraryScreenRenderingMixin
from xfinaudio.desktop.library_view_model import LibraryViewModel

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


class LibraryScreen(LibraryScreenRenderingMixin, QWidget):
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
        build_library_screen_ui(self, _COLUMNS, _MISSING_COLUMN)

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
            self.hide_duplicates_button: "Collapse near-duplicate versions of the same song into one row",
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
        # Hide Duplicates bypasses _on_quick_filter_changed's mutual-exclusion logic —
        # no mutual exclusion applies to it.
        self.hide_duplicates_button.clicked.connect(self._refresh_filter_state)
        self.clear_filters_button.clicked.connect(self._clear_quick_filters)
        self.settings_button.clicked.connect(self.settings_requested)
        self.help_button.clicked.connect(self._show_help)
        self.tour_button.clicked.connect(self._show_tour)
        self.tracks_table.horizontalHeader().sectionDoubleClicked.connect(self._on_header_double_clicked)

    def connect_signals(self, window: Any) -> None:
        self.tracks_table.itemSelectionChanged.connect(window._refresh_idle_action_state)
        self.search_input.textChanged.connect(window._search_debounce.start)
        self.folder_change_requested.connect(window.choose_folder)
        self.scan_requested.connect(window.scan_selected_folder)
        self.cancel_scan_requested.connect(window.cancel_scan)
        self.selection_changed.connect(window._on_library_selection_changed)
        self.metadata_screen_requested.connect(lambda: window.workflow_tabs.setCurrentIndex(5))
        self.proceed_button.clicked.connect(lambda: window.workflow_tabs.setCurrentIndex(1))
        self.settings_requested.connect(window._settings_controller.open_settings_dialog)
        self.filters_cleared.connect(window._library_controller.on_library_filters_cleared)
        self.track_play_requested.connect(window._library_controller.on_track_play_requested)
        self.play_requested.connect(window._library_controller.on_preview_play_requested)
        self.pause_requested.connect(window._audio_player.pause)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
