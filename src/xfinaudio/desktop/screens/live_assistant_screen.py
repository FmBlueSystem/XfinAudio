"""Live Assistant screen for real-time DJ performance support."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.library.models import TrackRecord


class _CandidateRow(QWidget):
    """A single candidate track row with preview, load, and alerts."""

    preview_requested = Signal(str)
    load_next_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._track_path = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._rank_label = QLabel("1")
        self._rank_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(self._rank_label)

        self._title_label = QLabel("—")
        self._title_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self._title_label)

        self._artist_label = QLabel("—")
        self._artist_label.setStyleSheet("font-size: 12px; color: #aaaaaa;")
        layout.addWidget(self._artist_label)

        self._bpm_label = QLabel("—")
        layout.addWidget(self._bpm_label)

        self._key_label = QLabel("—")
        layout.addWidget(self._key_label)

        self._energy_label = QLabel("—")
        layout.addWidget(self._energy_label)

        self._score_label = QLabel("—")
        self._score_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._score_label)

        self._alert_label = QLabel("")
        self._alert_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        layout.addWidget(self._alert_label)

        layout.addStretch()

        self._preview_button = QPushButton("▶")
        self._preview_button.setFixedWidth(32)
        self._preview_button.clicked.connect(self._on_preview)
        layout.addWidget(self._preview_button)

        self._load_button = QPushButton("Load Next")
        self._load_button.clicked.connect(self._on_load)
        layout.addWidget(self._load_button)

        self.setVisible(False)

    def set_candidate(self, rank: int, track: TrackRecord, score: float, alerts: list[str]) -> None:
        self._track_path = track.path
        self._rank_label.setText(str(rank))
        self._title_label.setText(track.title or "Unknown")
        self._artist_label.setText(track.artist or "Unknown")
        self._bpm_label.setText(f"{track.bpm:.1f}" if track.bpm else "—")
        self._key_label.setText(track.camelot_key or "—")
        self._energy_label.setText(str(track.energy_level) if track.energy_level else "—")
        self._score_label.setText(f"{score:.2f}")

        if alerts:
            self._alert_label.setText("  ⚠ " + "; ".join(alerts))
        else:
            self._alert_label.setText("")

        self.setVisible(True)

    def hide_row(self) -> None:
        self.setVisible(False)

    def _on_preview(self) -> None:
        if self._track_path:
            self.preview_requested.emit(self._track_path)

    def _on_load(self) -> None:
        if self._track_path:
            self.load_next_requested.emit(self._track_path)


class LiveAssistantScreen(QWidget):
    """Main Live Assistant screen with Now Playing, Suggestions, and Set History."""

    preview_requested = Signal(str)
    load_next_requested = Signal(str)
    exit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Live Assistant")

        self._current_track: TrackRecord | None = None
        self._candidates: list[TrackRecord] = []
        self._records_by_path: dict[str, TrackRecord] = {}
        self._scanned_records: list[TrackRecord] = []
        self._session_start = datetime.now()

        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("<h1>Live Assistant</h1>"))
        header.addStretch()
        self._exit_button = QPushButton("Exit")
        self._exit_button.clicked.connect(self.exit_requested.emit)
        header.addWidget(self._exit_button)
        layout.addLayout(header)

        self._guidance_label = QLabel(
            self.tr(
                "1. Pick a track to start the session (or use the candidate list). "
                "2. Preview candidates with the play button; alerts flag risky transitions. "
                "3. Press Load Next to commit the chosen track as the new current track. "
                "Shortcuts: Space plays or pauses preview; L loads the selected next track. "
                "Scan a library first to populate candidates."
            )
        )
        self._guidance_label.setObjectName("guidanceLabel")
        self._guidance_label.setWordWrap(True)
        layout.addWidget(self._guidance_label)

        # Empty state
        self._empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_state_widget)
        empty_layout.addWidget(
            QLabel("Scan or load a playlist to start Live Assistant"),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(self._empty_state_widget)

        # Content
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)

        # Now Playing
        now_playing_group = QVBoxLayout()
        now_playing_group.addWidget(QLabel("<h2>Now Playing</h2>"))
        np_row = QHBoxLayout()
        self._now_playing_title = QLabel("—")
        self._now_playing_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        np_row.addWidget(QLabel("Title:"))
        np_row.addWidget(self._now_playing_title)

        self._now_playing_artist = QLabel("—")
        np_row.addWidget(QLabel("Artist:"))
        np_row.addWidget(self._now_playing_artist)

        self._now_playing_bpm = QLabel("—")
        np_row.addWidget(QLabel("BPM:"))
        np_row.addWidget(self._now_playing_bpm)

        self._now_playing_key = QLabel("—")
        np_row.addWidget(QLabel("Key:"))
        np_row.addWidget(self._now_playing_key)

        self._now_playing_energy = QLabel("—")
        np_row.addWidget(QLabel("Energy:"))
        np_row.addWidget(self._now_playing_energy)

        self._timer_label = QLabel("00:00")
        self._timer_label.setStyleSheet("font-size: 16px; font-family: monospace;")
        np_row.addWidget(QLabel("Elapsed:"))
        np_row.addWidget(self._timer_label)
        np_row.addStretch()

        now_playing_group.addLayout(np_row)
        content_layout.addLayout(now_playing_group)

        # Suggestions
        suggestions_group = QVBoxLayout()
        suggestions_group.addWidget(QLabel("<h2>Next Suggestions</h2>"))

        self._suggestion_rows: list[_CandidateRow] = []
        for _rank in range(1, 4):
            row = _CandidateRow()
            row.preview_requested.connect(self.preview_requested.emit)
            row.load_next_requested.connect(self._on_load_next)
            self._suggestion_rows.append(row)
            suggestions_group.addWidget(row)

        content_layout.addLayout(suggestions_group)

        # Set History
        history_group = QVBoxLayout()
        history_group.addWidget(QLabel("<h2>Set History</h2>"))
        self._history_table = QTableWidget()
        self._history_table.setColumnCount(6)
        self._history_table.setHorizontalHeaderLabels(["#", "Title", "Artist", "BPM", "Key", "Time"])
        self._history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        history_group.addWidget(self._history_table)
        content_layout.addLayout(history_group)

        layout.addWidget(self._content_widget)
        self._content_widget.setVisible(False)

        # Timer
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_timer)
        self._elapsed_timer.start(1000)

        # Keyboard shortcuts
        self._shortcut_esc = QShortcut(Qt.Key.Key_Escape, self)
        self._shortcut_esc.activated.connect(self.exit_requested.emit)

        self._shortcut_space = QShortcut(Qt.Key.Key_Space, self)
        self._shortcut_space.activated.connect(self._on_space_load)

        for idx, key in enumerate([Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3], start=0):
            shortcut = QShortcut(key, self)
            shortcut.activated.connect(lambda i=idx: self._on_number_load(i))

    def set_current_track(self, track: TrackRecord) -> None:
        self._current_track = track
        self._now_playing_title.setText(track.title or "Unknown")
        self._now_playing_artist.setText(track.artist or "Unknown")
        self._now_playing_bpm.setText(f"{track.bpm:.1f}" if track.bpm else "—")
        self._now_playing_key.setText(track.camelot_key or "—")
        self._now_playing_energy.setText(str(track.energy_level) if track.energy_level else "—")
        self._session_start = datetime.now()
        self._update_timer()

        self._empty_state_widget.setVisible(False)
        self._content_widget.setVisible(True)
        self._guidance_label.setVisible(False)

    def set_candidates(self, candidates: list[TrackRecord]) -> None:
        self._candidates = candidates
        for idx, row in enumerate(self._suggestion_rows):
            if idx < len(candidates):
                track = candidates[idx]
                # Simple placeholder score; real scores come from recommendation engine
                score = max(0.95 - idx * 0.1, 0.0)
                alerts = self._generate_alerts(track)
                row.set_candidate(idx + 1, track, score, alerts)
            else:
                row.hide_row()

    def append_history(self, track: TrackRecord) -> None:
        row = self._history_table.rowCount()
        self._history_table.insertRow(row)
        self._history_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self._history_table.setItem(row, 1, QTableWidgetItem(track.title or "Unknown"))
        self._history_table.setItem(row, 2, QTableWidgetItem(track.artist or "Unknown"))
        self._history_table.setItem(row, 3, QTableWidgetItem(f"{track.bpm:.1f}" if track.bpm else "—"))
        self._history_table.setItem(row, 4, QTableWidgetItem(track.camelot_key or "—"))
        self._history_table.setItem(row, 5, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def set_library_state(self, records_by_path: dict[str, TrackRecord], scanned_records: list[TrackRecord]) -> None:
        """Provide the library state used by load-next suggestions."""
        self._records_by_path = records_by_path
        self._scanned_records = scanned_records

    def connect_signals(self, workflow_tabs, preview_handler) -> None:
        """Wire screen-local signals to the owning window."""
        self.exit_requested.connect(lambda: workflow_tabs().setCurrentIndex(0))
        self.preview_requested.connect(preview_handler)
        self.load_next_requested.connect(self.load_next)

    def load_next(self, path: str) -> None:
        """Handle load-next: update current track and recalculate suggestions."""
        record = self._records_by_path.get(path)
        if record is None:
            return
        self.set_current_track(record)
        candidates = [r for r in self._scanned_records if r.path != path and r.metadata_status == "complete"][:25]
        self.set_candidates(candidates)

    def _on_load_next(self, path: str) -> None:
        if self._current_track:
            self.append_history(self._current_track)
        self.load_next_requested.emit(path)

    def _on_space_load(self) -> None:
        if self._suggestion_rows and self._suggestion_rows[0].isVisible():
            self._suggestion_rows[0]._load_button.click()

    def _on_number_load(self, index: int) -> None:
        if index < len(self._suggestion_rows) and self._suggestion_rows[index].isVisible():
            self._suggestion_rows[index]._load_button.click()

    def _update_timer(self) -> None:
        elapsed = datetime.now() - self._session_start
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        self._timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _generate_alerts(self, candidate: TrackRecord) -> list[str]:
        alerts: list[str] = []
        if self._current_track is None:
            return alerts

        current = self._current_track
        if current.bpm and candidate.bpm and current.bpm > 0:
            diff = abs(candidate.bpm - current.bpm) / current.bpm
            if diff > 0.03:
                alerts.append(f"BPM +{diff * 100:.1f}%")

        if (
            current.camelot_key
            and candidate.camelot_key
            and not _camelot_compatible(current.camelot_key, candidate.camelot_key)
        ):
            alerts.append("Key clash")

        if (
            current.energy_level is not None
            and candidate.energy_level is not None
            and abs(candidate.energy_level - current.energy_level) > 2
        ):
            alerts.append("Energy jump")

        return alerts


def _camelot_compatible(left: str, right: str) -> bool:
    """Check if two Camelot keys are harmonically compatible."""
    if left == right:
        return True
    if len(left) < 2 or len(right) < 2:
        return False
    left_num = int(left[:-1])
    left_letter = left[-1]
    right_num = int(right[:-1])
    right_letter = right[-1]
    if left_letter == right_letter:
        diff = abs(left_num - right_num)
        return diff == 1 or diff == 11
    return left_num == right_num and left_letter != right_letter
