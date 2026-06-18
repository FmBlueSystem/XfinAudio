"""Undo toolbar facade for MainWindow."""

from __future__ import annotations

from PySide6.QtWidgets import QMenu, QPushButton, QToolBar, QWidget

from xfinaudio.desktop.undo_manager import UndoManager


class UndoToolbar:
    def __init__(self, undo_manager: UndoManager, parent: QWidget) -> None:
        self._undo_manager = undo_manager
        self._parent = parent
        toolbar = QToolBar(parent.tr("Undo/Redo"))
        toolbar.setObjectName("undoRedoToolbar")
        self._toolbar = toolbar
        self.undo_button = QPushButton(parent.tr("Undo"))
        self.undo_button.setObjectName("undoButton")
        self.undo_button.setToolTip(parent.tr("Undo last action (Ctrl+Z)"))
        self.undo_button.clicked.connect(self.undo)
        self.undo_history_menu = QMenu(self.undo_button)
        self.undo_button.setMenu(self.undo_history_menu)
        self.redo_button = QPushButton(parent.tr("Redo"))
        self.redo_button.setObjectName("redoButton")
        self.redo_button.setToolTip(parent.tr("Redo last undone action (Ctrl+Shift+Z)"))
        self.redo_button.clicked.connect(self.redo)
        toolbar.addWidget(self.undo_button)
        toolbar.addWidget(self.redo_button)
        self.refresh()

    @property
    def toolbar(self) -> QToolBar:
        return self._toolbar

    def undo(self) -> None:
        self._undo_manager.undo()
        self.refresh()

    def redo(self) -> None:
        self._undo_manager.redo()
        self.refresh()

    def refresh(self) -> None:
        self.undo_button.setEnabled(self._undo_manager.can_undo)
        self.redo_button.setEnabled(self._undo_manager.can_redo)
        self.undo_history_menu.clear()
        for label in self._undo_manager.history():
            self.undo_history_menu.addAction(label)
