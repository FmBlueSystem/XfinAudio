"""MyPlaylistsScreen — list and manage saved playlists."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.library.playlist_models import PlaylistSummary


class MyPlaylistsScreen(QWidget):
    """Displays saved playlists and emits CRUD signals."""

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
        toolbar.addWidget(self.create_button)
        toolbar.addWidget(self.rename_button)
        toolbar.addWidget(self.duplicate_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # List
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # Empty state label (shown when list is empty)
        self.empty_label = QLabel(self.tr("No saved playlists yet. Generate a playlist and click Save."))
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

    def _connect_signals(self) -> None:
        self.create_button.clicked.connect(self._on_create_clicked)
        self.rename_button.clicked.connect(self._on_rename_clicked)
        self.duplicate_button.clicked.connect(self._on_duplicate_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.list_widget.itemActivated.connect(self._on_item_activated)
        self.list_widget.itemDoubleClicked.connect(self._on_item_activated)

    def populate_list(self, summaries: list[PlaylistSummary]) -> None:
        """Refresh the playlist list from summaries."""
        self.list_widget.clear()
        for summary in summaries:
            text = f"{summary.name}  ({summary.track_count} tracks)"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, summary.id)
            self.list_widget.addItem(item)
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
        if playlist_id is not None:
            # Simple inline rename via dialog would go here
            self.rename_requested.emit(playlist_id, "")

    def _on_duplicate_clicked(self) -> None:
        playlist_id = self.selected_playlist_id()
        if playlist_id is not None:
            self.duplicate_requested.emit(playlist_id)

    def _on_delete_clicked(self) -> None:
        playlist_id = self.selected_playlist_id()
        if playlist_id is not None:
            self.delete_requested.emit(playlist_id)
