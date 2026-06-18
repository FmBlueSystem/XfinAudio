"""PlaylistEditor — edit a playlist's track order and contents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.library.playlist_models import Playlist


class PlaylistEditor(QWidget):
    """Edit a single playlist's tracks."""

    track_removed = Signal(str)
    tracks_reordered = Signal(list)
    export_requested = Signal(int)
    save_requested = Signal(int, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._playlist_id: int | None = None
        self._track_paths: list[str] = []
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.name_label = QLabel()
        layout.addWidget(self.name_label)

        # Tracks table
        self.tracks_table = QTableWidget(0, 5)
        self.tracks_table.setHorizontalHeaderLabels(
            [self.tr("#"), self.tr("Title"), self.tr("Artist"), self.tr("BPM"), self.tr("Actions")]
        )
        header = self.tracks_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tracks_table.setSelectionBehavior(self.tracks_table.SelectionBehavior.SelectRows)
        self.tracks_table.verticalHeader().setVisible(False)
        layout.addWidget(self.tracks_table)

        # Toolbar
        toolbar = QHBoxLayout()
        self.export_button = QPushButton(self.tr("Export to Serato"))
        self.save_button = QPushButton(self.tr("Save"))
        toolbar.addStretch()
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.save_button)
        layout.addLayout(toolbar)

    def _connect_signals(self) -> None:
        self.export_button.clicked.connect(self._on_export_clicked)
        self.save_button.clicked.connect(self._on_save_clicked)

    def connect_signals(self, window: Any) -> None:
        _ = window

    def set_playlist(self, playlist: Playlist) -> None:
        """Load a playlist into the editor."""
        self._playlist_id = playlist.id
        self._track_paths = list(playlist.track_paths)
        self.name_label.setText(f"<b>{playlist.name}</b>")
        self._populate_table()

    def _populate_table(self) -> None:
        self.tracks_table.setRowCount(0)
        for idx, path in enumerate(self._track_paths):
            row = self.tracks_table.rowCount()
            self.tracks_table.insertRow(row)
            filename = Path(path).name
            self.tracks_table.setItem(row, 0, QTableWidgetItem(str(idx + 1)))
            self.tracks_table.setItem(row, 1, QTableWidgetItem(filename))
            self.tracks_table.setItem(row, 2, QTableWidgetItem("—"))
            self.tracks_table.setItem(row, 3, QTableWidgetItem("—"))
            remove_btn = QPushButton(self.tr("Remove"))
            remove_btn.clicked.connect(lambda checked=False, r=row: self._on_remove_clicked(r))
            self.tracks_table.setCellWidget(row, 4, remove_btn)

    def _on_remove_clicked(self, row: int) -> None:
        if 0 <= row < len(self._track_paths):
            path = self._track_paths.pop(row)
            self._populate_table()
            self.track_removed.emit(path)

    def _on_export_clicked(self) -> None:
        if self._playlist_id is not None:
            self.export_requested.emit(self._playlist_id)

    def _on_save_clicked(self) -> None:
        if self._playlist_id is not None:
            self.save_requested.emit(self._playlist_id, list(self._track_paths))
