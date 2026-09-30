"""MyPlaylistsScreen — list and manage saved playlists."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.library.playlist_models import Playlist, PlaylistSummary


class MyPlaylistsScreen(QWidget):
    """Displays saved playlists and emits CRUD signals."""

    query_requested = Signal(str)
    compare_requested = Signal(list)
    open_requested = Signal(int)
    create_requested = Signal()
    rename_requested = Signal(int, str)
    duplicate_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        self.create_button = QPushButton(self.tr("New Playlist"))
        self.rename_button = QPushButton(self.tr("Rename"))
        self.duplicate_button = QPushButton(self.tr("Duplicate"))
        self.delete_button = QPushButton(self.tr("Delete"))
        for button, tip in (
            (self.create_button, "Create an empty playlist"),
            (self.rename_button, "Rename the selected playlist"),
            (self.duplicate_button, "Copy the selected playlist under a new name"),
            (self.delete_button, "Delete the selected playlist permanently"),
        ):
            button.setToolTip(self.tr(tip))
        toolbar.addWidget(self.create_button)
        toolbar.addWidget(self.rename_button)
        toolbar.addWidget(self.duplicate_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText(self.tr("Offline: find house playlists / compare Sunset and Peak"))
        self.find_button = QPushButton(self.tr("Find / compare"))
        self.compare_button = QPushButton(self.tr("Compare selected"))
        query_row = QHBoxLayout()
        query_row.addWidget(self.query_input)
        query_row.addWidget(self.find_button)
        query_row.addWidget(self.compare_button)
        layout.addLayout(query_row)
        self.assistant_output = QPlainTextEdit()
        self.assistant_output.setReadOnly(True)
        self.assistant_output.setMaximumHeight(150)
        self.assistant_output.setPlaceholderText(
            self.tr("Local saved-set evidence only. Select multiple sets to compare.")
        )
        layout.addWidget(self.assistant_output)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(self.list_widget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.list_widget)

        # Empty state label (shown when list is empty)
        self.empty_label = QLabel(self.tr("No saved playlists yet. Generate a playlist and click Save."))
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

    def _connect_signals(self) -> None:
        self.find_button.clicked.connect(lambda: self.query_requested.emit(self.query_input.text()))
        self.query_input.returnPressed.connect(lambda: self.query_requested.emit(self.query_input.text()))
        self.compare_button.clicked.connect(
            lambda: self.compare_requested.emit(
                [item.data(Qt.ItemDataRole.UserRole) for item in self.list_widget.selectedItems()]
            )
        )
        self.create_button.clicked.connect(self._on_create_clicked)
        self.rename_button.clicked.connect(self._on_rename_clicked)
        self.duplicate_button.clicked.connect(self._on_duplicate_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.list_widget.itemActivated.connect(self._on_item_activated)
        self.list_widget.itemDoubleClicked.connect(self._on_item_activated)

    def connect_signals(self, window: Any) -> None:
        _ = window

    def populate_list(self, summaries: list[PlaylistSummary]) -> None:
        """Refresh the playlist list from summaries."""
        self.list_widget.clear()
        for summary in summaries:
            text = f"{summary.name}  ({summary.track_count} tracks)"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, summary.id)
            self.list_widget.addItem(item)
        self.empty_label.setText(self.tr("No saved playlists yet. Generate a playlist and click Save."))
        self.empty_label.setVisible(len(summaries) == 0)

    def selected_playlist_id(self) -> int | None:
        """Return the id of the currently selected playlist, or None."""
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_item_activated(self, item: QListWidgetItem | None) -> None:
        if item is not None:
            playlist_id = item.data(Qt.ItemDataRole.UserRole)
            self.open_requested.emit(playlist_id)

    def _on_create_clicked(self) -> None:
        self.create_requested.emit()

    def _on_rename_clicked(self) -> None:
        playlist_id = self.selected_playlist_id()
        if playlist_id is None:
            return
        item = self.list_widget.currentItem()
        current_name = "" if item is None else item.text().split("  (", maxsplit=1)[0]
        name, accepted = QInputDialog.getText(
            self,
            self.tr("Rename Playlist"),
            self.tr("Playlist name:"),
            QLineEdit.EchoMode.Normal,
            current_name,
        )
        new_name = name.strip()
        if accepted and new_name:
            self.rename_requested.emit(playlist_id, new_name)

    def _on_duplicate_clicked(self) -> None:
        playlist_id = self.selected_playlist_id()
        if playlist_id is not None:
            self.duplicate_requested.emit(playlist_id)

    def _on_delete_clicked(self) -> None:
        playlist_id = self.selected_playlist_id()
        if playlist_id is not None:
            self.delete_requested.emit(playlist_id)

    def show_assistant_result(self, playlists: list[Playlist], text: str) -> None:
        self.populate_list(
            [PlaylistSummary(p.id, p.name, len(p.track_paths), p.updated_at) for p in playlists if p.id is not None]
        )
        self.assistant_output.setPlainText(text)
        if not playlists:
            self.empty_label.setText(self.tr("No saved playlists match. Clear the query to show all saved sets."))
