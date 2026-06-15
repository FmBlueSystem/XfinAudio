"""Compact bottom status bar for library scanning context."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusBar(QWidget):
    """Three-section status bar for folder, guidance, and scan progress."""

    def __init__(self, folder_label: QLabel, guidance_label: QLabel, scan_progress_label: QLabel) -> None:
        super().__init__()
        self.folder_label = folder_label
        self.guidance_label = guidance_label
        self.scan_progress_label = scan_progress_label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.folder_label)
        layout.addWidget(self.guidance_label, 1)
        layout.addWidget(self.scan_progress_label)
