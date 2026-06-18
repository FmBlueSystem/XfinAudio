"""Workflow stack widget used by the desktop shell."""

from __future__ import annotations

from PySide6.QtWidgets import QStackedWidget


class WorkflowStack(QStackedWidget):
    """QStackedWidget with the tab-like compatibility API used by coordinators/tests."""

    def __init__(self, labels: list[str]) -> None:
        super().__init__()
        self._labels = labels
        self._enabled = [True for _ in labels]

    def tabText(self, index: int) -> str:
        """Return the navigation label for compatibility with the previous QTabWidget."""
        return self._labels[index]

    def setTabEnabled(self, index: int, enabled: bool) -> None:
        """Store per-screen navigation enablement for the sidebar-backed stack."""
        if 0 <= index < len(self._enabled):
            self._enabled[index] = enabled
            screen = self.widget(index)
            if screen is not None:
                screen.setEnabled(enabled)

    def isTabEnabled(self, index: int) -> bool:
        """Return whether a screen can be selected."""
        return 0 <= index < len(self._enabled) and self._enabled[index]

    def setCurrentIndex(self, index: int) -> None:
        """Keep programmatic navigation compatible with the previous workflow_tabs alias."""
        super().setCurrentIndex(index)
