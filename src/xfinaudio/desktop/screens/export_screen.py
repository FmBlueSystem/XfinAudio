"""ExportScreen — thin QWidget that renders ExportViewModel data."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.scan_controller import progress_percent, progress_status_text

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
        layout.addWidget(self.playlist_info_label)

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
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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
        self.history_table.setAccessibleName(self.tr("Export history"))
        self.back_button.setAccessibleName(self.tr("Back to review"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.software_selector, self.safe_folder_button)
        self.setTabOrder(self.safe_folder_button, self.preview_button)
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
