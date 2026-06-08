"""ExportScreen — thin QWidget that renders ExportViewModel data."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel

_HISTORY_COLUMNS = ["Time", "Strategy", "Tracks", "Serato Crate", "Readiness JSON", "Readiness CSV"]


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
        self.safe_folder_button = QPushButton(self.tr("Choose Folder"))
        info_row.addWidget(self.variant_label)
        info_row.addStretch()
        info_row.addWidget(self.safe_folder_label)
        info_row.addWidget(self.safe_folder_button)
        layout.addLayout(info_row)

        # Export guidance label (set imperatively by main_window)
        self.export_guidance_label = QLabel(
            self.tr("Review recommendations before exporting; desktop export setup is intentionally out of scope.")
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
        self.export_button = QPushButton(self.tr("Export to Serato"))
        self.export_button.setObjectName("seratoExportButton")
        self.export_button.setEnabled(False)
        self.export_readiness_button = QPushButton(self.tr("Export Readiness Report"))
        self.export_readiness_button.setEnabled(False)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.export_readiness_button)
        actions.addStretch()
        layout.addLayout(actions)

        # Export history table (hidden until first export) — absorbs all spare vertical space.
        self.history_table = QTableWidget(0, len(_HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels([self.tr(c) for c in _HISTORY_COLUMNS])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.history_table.setMinimumHeight(200)
        self.history_table.setVisible(False)
        layout.addWidget(self.history_table, 1)

        # Navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton(self.tr("← Review"))
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
        self.playlist_info_label.setText(vm.preview_text(state) or "—")
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
