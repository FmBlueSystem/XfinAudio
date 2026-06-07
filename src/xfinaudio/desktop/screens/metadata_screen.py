"""MetadataScreen — thin QWidget for displaying metadata scan info."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState


class MetadataScreen(QWidget):
    """Displays metadata information from AppState."""

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

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        layout.addStretch()

        nav = QHBoxLayout()
        self.back_button = QPushButton("← Library")
        nav.addWidget(self.back_button)
        nav.addStretch()
        layout.addLayout(nav)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, state: AppState) -> None:
        """Update widgets from AppState."""
        track_count = len(state.scanned_records)
        if track_count == 0:
            self.status_label.setText("No tracks loaded")
        else:
            complete = sum(1 for t in state.scanned_records if t.metadata_status == "complete")
            self.status_label.setText(f"{track_count} tracks · {complete}/{track_count} complete")
