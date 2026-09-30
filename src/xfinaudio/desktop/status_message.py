"""Compact status text with the complete message available accessibly."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy


class StatusMessage(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMaximumHeight(48)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setText(text)

    def setText(self, text: str) -> None:
        super().setText(text)
        self.setToolTip(text)
        self.setAccessibleDescription(text)
