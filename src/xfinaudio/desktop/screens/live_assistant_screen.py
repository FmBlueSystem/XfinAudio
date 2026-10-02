"""Live Assistant screen for real-time DJ performance support."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.live_assistance import LiveCandidate, live_session_ready, rank_live_candidates
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessReport
from xfinaudio.recommendation.camelot import score_camelot_transition
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import bpm_difference_percent, effective_energy_delta


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
        self._artist_label.setStyleSheet("font-size: 12px; color: #93aac4;")
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
        self._preview_button.setMinimumHeight(32)
        # The glyph alone says nothing on screen and nothing at all to a screen
        # reader, so both the tooltip and the accessible name carry the meaning.
        self._preview_button.setToolTip(self.tr("Preview this suggestion"))
        self._preview_button.setAccessibleName(self.tr("Preview this suggestion"))
        self._preview_button.clicked.connect(self._on_preview)
        layout.addWidget(self._preview_button)

        self._load_button = QPushButton("Load Next")
        self._load_button.setMinimumHeight(32)
        self._load_button.setToolTip(self.tr("Load this suggestion as the next track"))
        self._load_button.clicked.connect(self._on_load)
        layout.addWidget(self._load_button)

        self.hide_row()

    def set_candidate(self, rank: int, track: TrackRecord, score: float, alerts: list[str]) -> None:
        self._track_path = track.path
        self._load_button.setEnabled(True)
        self._preview_button.setEnabled(True)
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
        self._track_path = ""
        self._load_button.setEnabled(False)
        self._preview_button.setEnabled(False)
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
        self._session_recommendation: PlaylistRecommendation | None = None
        self._session_readiness: DjReadinessReport | None = None
        self._session_signature: tuple | None = None
        self._played_paths: tuple[str, ...] = ()
        self._ranked_candidates: list[LiveCandidate] = []
        self._locked_paths: frozenset[str] = frozenset()
        self._excluded_paths: frozenset[str] = frozenset()
        self._spectral_cohesion = 0.0

        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("<h1>Live Assistant</h1>"))
        header.addStretch()
        self._exit_button = QPushButton("Exit")
        self._exit_button.setToolTip(self.tr("Leave Live Assistant and return to the workflow"))
        self._exit_button.clicked.connect(self.exit_requested.emit)
        header.addWidget(self._exit_button)
        layout.addLayout(header)

        self._guidance_label = QLabel(
            self.tr(
                "1. Pick a track to start the session (or use the candidate list). "
                "2. Preview candidates with the play button; alerts flag risky transitions. "
                "3. Press Load Next to commit the chosen track as the new current track. "
                "Shortcuts: Space or 1 loads the first suggestion; "
                "2 and 3 load the second and third suggestions; Esc exits. "
                "Scan a library first to populate candidates."
            )
        )
        self._guidance_label.setObjectName("guidanceLabel")
        self._guidance_label.setWordWrap(True)
        layout.addWidget(self._guidance_label)

        self._context_label = QLabel(self.tr("Apply a ready set in Review to start local Live guidance."))
        self._context_label.setWordWrap(True)
        layout.addWidget(self._context_label)

        # Empty state
        self._empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_state_widget)
        empty_layout.addWidget(
            QLabel("Apply a ready recommendation to start Live Assistant"),
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(self._empty_state_widget)

        # Content
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)

        # Now Playing
        now_playing_group = QVBoxLayout()
        now_playing_group.addWidget(QLabel("<h2>Current track (manual)</h2>"))
        np_row = QHBoxLayout()
        self._now_playing_title = QLabel("—")
        self._now_playing_title.setWordWrap(True)
        self._now_playing_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        np_row.addWidget(QLabel("Title:"))
        np_row.addWidget(self._now_playing_title)

        self._now_playing_artist = QLabel("—")
        self._now_playing_artist.setWordWrap(True)
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
            row.preview_requested.connect(self._preview_candidate)
            row.load_next_requested.connect(self._on_load_next)
            self._suggestion_rows.append(row)
            suggestions_group.addWidget(row)

        content_layout.addLayout(suggestions_group)

        # Set History
        history_group = QVBoxLayout()
        history_group.addWidget(QLabel("<h2>Set History</h2>"))
        self._history_table = QTableWidget()
        self._history_table.setMinimumHeight(130)
        self._history_table.setColumnCount(6)
        self._history_table.setHorizontalHeaderLabels(["#", "Title", "Artist", "BPM", "Key", "Time"])
        self._history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        history_header = self._history_table.horizontalHeader()
        history_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for column in (0, 3, 4, 5):
            history_header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        history_group.addWidget(self._history_table)
        content_layout.addLayout(history_group, 1)

        # Preserve readable candidate actions when commentary uses vertical
        # space. The session scrolls rather than forcing the window taller.
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setWidget(self._content_widget)
        layout.addWidget(self.content_scroll, 1)
        self._content_widget.setVisible(False)

        # Timer. Started by set_current_track(), not here: the screen is built
        # for every session but most never open it, and an idle screen has no
        # elapsed time to show.
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_timer)

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
        self._elapsed_timer.start(1000)

        self._empty_state_widget.setVisible(False)
        self._content_widget.setVisible(True)
        self._guidance_label.setVisible(False)

    def set_candidates(self, candidates: list[TrackRecord]) -> None:
        """Display only freshly validated members of the applied session pool."""
        self._ranked_candidates = []
        if self._session_recommendation is not None:
            self._ranked_candidates = rank_live_candidates(
                self._session_recommendation,
                self._played_paths,
                locked_paths=self._locked_paths,
                excluded_paths=self._excluded_paths,
                spectral_cohesion=self._spectral_cohesion,
            )
        allowed = {track.path for track in candidates}
        self._ranked_candidates = [item for item in self._ranked_candidates if item.track.path in allowed]
        self._candidates = [item.track for item in self._ranked_candidates]
        for idx, row in enumerate(self._suggestion_rows):
            if idx < len(self._ranked_candidates):
                item = self._ranked_candidates[idx]
                row.set_candidate(idx + 1, item.track, item.score.total_score, item.score.warnings)
                row.setToolTip("Local engine: " + "; ".join(item.score.explanations) + "\n" + item.readiness.summary)
            else:
                row.hide_row()
        if self._session_recommendation is not None:
            self._context_label.setText(
                self.tr(
                    "Local engine scores; only ready continuations from this set. "
                    "Manual track selection, not playback detection."
                )
                if self._ranked_candidates
                else self.tr("No ready continuation remains in this set.")
            )

    def set_session(
        self,
        recommendation: PlaylistRecommendation | None,
        readiness: DjReadinessReport | None,
        *,
        locked_paths: frozenset[str] = frozenset(),
        excluded_paths: frozenset[str] = frozenset(),
        spectral_cohesion: float = 0.0,
    ) -> bool:
        """Bind an idempotent safe session; context changes invalidate all old actions."""
        if not live_session_ready(
            recommendation,
            readiness,
            locked_paths=locked_paths,
            excluded_paths=excluded_paths,
            spectral_cohesion=spectral_cohesion,
        ):
            self.clear_session()
            return False
        assert recommendation is not None and readiness is not None
        signature = (
            id(recommendation),
            recommendation.model_dump_json(),
            id(readiness),
            readiness.model_dump_json(),
            locked_paths,
            excluded_paths,
            spectral_cohesion,
        )
        if signature == self._session_signature:
            return True
        self.clear_session()
        self._session_signature = signature
        self._session_recommendation = recommendation
        self._session_readiness = readiness
        self._locked_paths, self._excluded_paths = locked_paths, excluded_paths
        self._spectral_cohesion = spectral_cohesion
        first = recommendation.ordered_tracks[0]
        self._played_paths = (first.path,)
        self.set_current_track(first)
        self.set_candidates(recommendation.ordered_tracks)
        return True

    def clear_session(self) -> None:
        self._session_recommendation = None
        self._session_readiness = None
        self._session_signature = None
        self._current_track = None
        self._played_paths = ()
        self._ranked_candidates = []
        self._candidates = []
        self._elapsed_timer.stop()
        self._history_table.setRowCount(0)
        for row in self._suggestion_rows:
            row.hide_row()
        self._content_widget.setVisible(False)
        self._empty_state_widget.setVisible(True)
        self._guidance_label.setVisible(True)
        self._context_label.setText(self.tr("Apply a ready set in Review to start local Live guidance."))

    def _preview_candidate(self, path: str) -> None:
        if self._session_recommendation is not None:
            self.set_candidates(self._session_recommendation.ordered_tracks)
        if any(item.track.path == path for item in self._ranked_candidates):
            self.preview_requested.emit(path)

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

    def connect_signals(self, window: Any) -> None:
        """Wire screen-local signals to the owning window."""
        self.exit_requested.connect(lambda: window.workflow_tabs.setCurrentIndex(0))
        self.preview_requested.connect(window._library_controller.on_preview_play_requested)

    def load_next(self, path: str) -> None:
        """Commit only a freshly validated next choice, never a raw library path."""
        recommendation = self._session_recommendation
        if recommendation is None:
            return
        self.set_candidates(recommendation.ordered_tracks)
        candidate = next((item.track for item in self._ranked_candidates if item.track.path == path), None)
        if candidate is None or self._current_track is None:
            return
        self.append_history(self._current_track)
        self._played_paths = (*self._played_paths, path)
        self.set_current_track(candidate)
        self.set_candidates(recommendation.ordered_tracks)

    def _on_load_next(self, path: str) -> None:
        previous = self._played_paths
        self.load_next(path)
        if previous != self._played_paths:
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
            diff_percent = bpm_difference_percent(current.bpm, candidate.bpm)
            if diff_percent > 3.0:
                alerts.append(f"BPM +{diff_percent:.1f}%")

        if (
            current.camelot_key
            and candidate.camelot_key
            and not (score_camelot_transition(current.camelot_key, candidate.camelot_key) > 0)
        ):
            alerts.append("Key clash")

        if (
            current.energy_level is not None
            and candidate.energy_level is not None
            and effective_energy_delta(current, candidate)[0] > 2
        ):
            alerts.append("Energy jump")

        return alerts
