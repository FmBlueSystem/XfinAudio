"""PlaylistEditor — edit a playlist's track order and contents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.application.playlist_edit_assessment import assess_playlist_edit
from xfinaudio.application.playlist_edit_intents import propose_edit, validate_edit
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist


class PlaylistEditor(QWidget):
    """Edit a single playlist's tracks."""

    back_requested = Signal()
    preview_requested = Signal(str)
    confirm_requested = Signal()
    track_removed = Signal(str)
    tracks_reordered = Signal(list)
    export_requested = Signal(int)
    save_requested = Signal(int, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._playlist_id: int | None = None
        self._track_paths: list[str] = []
        self._saved_paths: tuple[str, ...] = ()
        self._records: list[TrackRecord] = []
        self._locked_paths: frozenset[str] = frozenset()
        self._excluded_paths: frozenset[str] = frozenset()
        self._preview: tuple[str, ...] | None = None
        self.session_revision = 0
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.back_button = QPushButton(self.tr("Back to My Playlists"))
        layout.addWidget(self.back_button)
        self.name_label = QLabel()
        self.name_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.name_label)

        self.edit_input = QLineEdit()
        self.edit_input.setPlaceholderText(self.tr("Offline: shorten to 10 tracks / raise energy / baja la energía"))
        layout.addWidget(self.edit_input)
        edit_actions = QHBoxLayout()
        self.preview_button = QPushButton(self.tr("Preview edit"))
        self.confirm_button = QPushButton(self.tr("Apply preview to draft"))
        self.cancel_preview_button = QPushButton(self.tr("Dismiss preview"))
        self.confirm_button.setEnabled(False)
        for button in (self.preview_button, self.confirm_button, self.cancel_preview_button):
            edit_actions.addWidget(button)
        layout.addLayout(edit_actions)
        self.status_label = QLabel(self.tr("Offline assistant. Preview → Apply to draft → Save."))
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(130)
        self.preview_text.hide()
        layout.addWidget(self.preview_text)

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
        self.tracks_table.setEditTriggers(self.tracks_table.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tracks_table)

        # Toolbar
        toolbar = QHBoxLayout()
        self.export_button = QPushButton(self.tr("Export to Serato"))
        self.export_button.setToolTip(self.tr("Write this playlist to your Serato crates"))
        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.setToolTip(self.tr("Save changes to this playlist"))
        self.move_up_button = QPushButton(self.tr("Move up"))
        self.move_down_button = QPushButton(self.tr("Move down"))
        self.cancel_button = QPushButton(self.tr("Discard draft"))
        toolbar.addWidget(self.move_up_button)
        toolbar.addWidget(self.move_down_button)
        toolbar.addWidget(self.cancel_button)
        toolbar.addStretch()
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.save_button)
        layout.addLayout(toolbar)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested.emit)
        self.preview_button.clicked.connect(lambda: self.preview_requested.emit(self.edit_input.text()))
        self.edit_input.returnPressed.connect(lambda: self.preview_requested.emit(self.edit_input.text()))
        self.edit_input.textChanged.connect(self.dismiss_preview)
        self.confirm_button.clicked.connect(self.confirm_requested.emit)
        self.cancel_preview_button.clicked.connect(self.dismiss_preview)
        self.cancel_button.clicked.connect(self.discard_draft)
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))
        self.export_button.clicked.connect(self._on_export_clicked)
        self.save_button.clicked.connect(self._on_save_clicked)

    def connect_signals(self, window: Any) -> None:
        _ = window

    def set_playlist(self, playlist: Playlist) -> None:
        """Load a playlist into the editor."""
        self._playlist_id = playlist.id
        self._track_paths = list(playlist.track_paths)
        self._saved_paths = tuple(playlist.track_paths)
        self.session_revision += 1
        self.name_label.setText(playlist.name)
        self.dismiss_preview()
        self.status_label.setText(self.tr("Saved version. Edits stay in a draft until Save."))
        self._populate_table()

    def _populate_table(self) -> None:
        self.tracks_table.setRowCount(0)
        for idx, path in enumerate(self._track_paths):
            row = self.tracks_table.rowCount()
            self.tracks_table.insertRow(row)
            record = next((r for r in self._records if r.path == path), None)
            filename = record.title if record and record.title else Path(path).name
            if path in self._locked_paths:
                filename += self.tr(" [locked]")
            if path in self._excluded_paths:
                filename += self.tr(" [excluded]")
            self.tracks_table.setItem(row, 0, QTableWidgetItem(str(idx + 1)))
            self.tracks_table.setItem(row, 1, QTableWidgetItem(filename))
            self.tracks_table.setItem(row, 2, QTableWidgetItem(record.artist if record and record.artist else "—"))
            self.tracks_table.setItem(row, 3, QTableWidgetItem(str(record.bpm) if record and record.bpm else "—"))
            remove_btn = QPushButton(self.tr("Remove"))
            remove_btn.setEnabled(path not in self._locked_paths)
            remove_btn.clicked.connect(lambda checked=False, r=row: self._on_remove_clicked(r))
            self.tracks_table.setCellWidget(row, 4, remove_btn)

    def _on_remove_clicked(self, row: int) -> None:
        if 0 <= row < len(self._track_paths) and self._track_paths[row] not in self._locked_paths:
            path = self._track_paths.pop(row)
            self.dismiss_preview()
            self._populate_table()
            self.status_label.setText(self.tr("Unsaved draft. Save or discard your changes."))
            self.track_removed.emit(path)

    def _on_export_clicked(self) -> None:
        if self._playlist_id is not None and not self.is_dirty:
            self.export_requested.emit(self._playlist_id)

    def _on_save_clicked(self) -> None:
        if self._playlist_id is not None:
            self.save_requested.emit(self._playlist_id, list(self._track_paths))

    @property
    def is_dirty(self) -> bool:
        return tuple(self._track_paths) != self._saved_paths

    def set_context(
        self,
        records: list[TrackRecord],
        *,
        locked_paths: frozenset[str] = frozenset(),
        excluded_paths: frozenset[str] = frozenset(),
    ) -> None:
        context = (records, locked_paths, excluded_paths)
        if context != (self._records, self._locked_paths, self._excluded_paths):
            self._records = list(records)
            self._locked_paths, self._excluded_paths = locked_paths, excluded_paths
            self.dismiss_preview()
            self._populate_table()

    def dismiss_preview(self, *_args: object) -> None:
        had_preview = self._preview is not None
        self._preview = None
        self.confirm_button.setEnabled(False)
        self.preview_text.clear()
        self.preview_text.hide()
        self.export_button.setEnabled(not self.is_dirty)
        if had_preview:
            self.status_label.setText(self.tr("Preview dismissed or stale. Request a new preview."))

    def preview_edit(self, request: str) -> None:
        self.dismiss_preview()
        try:
            self._preview = propose_edit(
                request,
                self._track_paths,
                self._records,
                locked_paths=self._locked_paths,
                excluded_paths=self._excluded_paths,
            )
            assessment = assess_playlist_edit(
                self._preview,
                self._records,
                locked_paths=self._locked_paths,
                excluded_paths=self._excluded_paths,
            )
        except ValueError as error:
            self._preview = None
            self.status_label.setText(str(error))
            return
        titles = {r.path: r.title or Path(r.path).name for r in self._records}
        self.preview_text.setPlainText(
            "\n".join(f"{index + 1}. {titles.get(path, Path(path).name)}" for index, path in enumerate(self._preview))
        )
        self.preview_text.appendPlainText("\n" + assessment.description)
        self.preview_text.show()
        self.confirm_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.status_label.setText(
            self.tr(
                "Preview: {before} → {after} tracks. Energy requests order known energy; "
                "no audio changes. Apply, then Save."
            ).format(before=len(self._track_paths), after=len(self._preview))
        )

    def confirm_preview(self) -> None:
        if self._preview is not None:
            self.apply_order(list(self._preview))

    def apply_order(self, paths: list[str]) -> bool:
        try:
            validate_edit(
                self._track_paths, paths, locked_paths=self._locked_paths, excluded_paths=self._excluded_paths
            )
        except ValueError as error:
            self.status_label.setText(str(error))
            self.dismiss_preview()
            return False
        self._track_paths = list(paths)
        self.dismiss_preview()
        self._populate_table()
        self.status_label.setText(self.tr("Unsaved draft. Save or discard your changes."))
        return True

    def discard_draft(self) -> None:
        self._track_paths = list(self._saved_paths)
        self.session_revision += 1
        self.dismiss_preview()
        self._populate_table()
        self.status_label.setText(self.tr("Draft discarded. Saved version restored."))

    def _move_selected(self, delta: int) -> None:
        row = self.tracks_table.currentRow()
        target = row + delta
        if 0 <= row < len(self._track_paths) and 0 <= target < len(self._track_paths):
            if {self._track_paths[row], self._track_paths[target]} & self._locked_paths:
                self.status_label.setText(self.tr("Unlock the track before moving its position."))
                return
            paths = list(self._track_paths)
            paths[row], paths[target] = paths[target], paths[row]
            self.tracks_reordered.emit(paths)
            self.tracks_table.selectRow(target)

    def clear_playlist(self) -> None:
        self._playlist_id = None
        self._saved_paths = ()
        self.name_label.clear()
        self.discard_draft()
        self.status_label.setText(self.tr("Open a saved playlist to edit it."))
