"""Qt-based audio player wrapper for track preview.

Uses PySide6.QtMultimedia.QMediaPlayer with no DSP, no analysis, no mixing.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from xfinaudio.desktop.audio_player_state import PlayerState, PlayerStateMachine


class AudioPlayer(QObject):
    """Thin wrapper around QMediaPlayer with a deterministic state machine.

    Signals
    -------
    state_changed(PlayerState)
        Emitted whenever the internal state machine transitions.
    position_changed(int)
        Emitted when playback position changes (milliseconds).
    duration_changed(int)
        Emitted when media duration becomes known (milliseconds).
    error_occurred(str)
        Emitted when QMediaPlayer reports an error.
    """

    state_changed = Signal(PlayerState)
    position_changed = Signal(int)
    duration_changed = Signal(int)
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source_path: str | None = None
        self._state_machine = PlayerStateMachine(on_transition=self._on_transition)

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.7)

        # Wire Qt signals
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.errorOccurred.connect(self._on_player_error)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)

        # Emit initial idle state after signals are wired
        self.state_changed.emit(PlayerState.IDLE)

    # --- Public API ---

    @property
    def state(self) -> PlayerState:
        return self._state_machine.state

    @property
    def position(self) -> int:
        return self._player.position()

    @property
    def duration(self) -> int:
        return self._player.duration()

    @property
    def volume(self) -> float:
        return self._audio_output.volume()

    def set_volume(self, value: float) -> None:
        """Clamp *value* to [0.0, 1.0] and apply."""
        clamped = max(0.0, min(1.0, float(value)))
        self._audio_output.setVolume(clamped)

    def load(self, path: str) -> None:
        """Load *path* and begin buffering."""
        self._source_path = path
        self._state_machine.transition("load")
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def play(self) -> None:
        """Resume from PAUSED."""
        if self._state_machine.state != PlayerState.PAUSED:
            raise RuntimeError(f"Cannot play from state {self._state_machine.state.name}")
        self._player.play()

    def pause(self) -> None:
        """Pause active playback."""
        if self._state_machine.state not in (PlayerState.PLAYING, PlayerState.PAUSED):
            raise RuntimeError(f"Cannot pause from state {self._state_machine.state.name}")
        self._player.pause()

    def stop(self) -> None:
        """Stop and return to IDLE."""
        self._player.stop()
        self._state_machine.transition("stop")

    def seek(self, ms: int) -> None:
        """Seek to *ms* milliseconds."""
        if self._state_machine.state in (PlayerState.IDLE, PlayerState.ERROR):
            raise RuntimeError(f"Cannot seek from state {self._state_machine.state.name}")
        self._player.setPosition(ms)

    # --- Private handlers ---

    def _on_transition(self, old: PlayerState, new: PlayerState, event: str) -> None:
        self.state_changed.emit(new)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            # Media loaded successfully — QMediaPlayer.play() was already called
            pass
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.error_occurred.emit(f"Invalid media: {self._source_path}")
            if self._state_machine.state != PlayerState.ERROR:
                self._state_machine.transition("error")

    def _on_playback_state_changed(self, playback_state: QMediaPlayer.PlaybackState) -> None:
        current = self._state_machine.state
        if playback_state == QMediaPlayer.PlaybackState.PlayingState and current == PlayerState.LOADING:
            self._state_machine.transition("play")
        elif playback_state == QMediaPlayer.PlaybackState.PausedState and current == PlayerState.PLAYING:
            self._state_machine.transition("pause")
        elif playback_state == QMediaPlayer.PlaybackState.StoppedState and current != PlayerState.IDLE:
            self._state_machine.transition("stop")

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        message = error_string or f"Media error {error.name}"
        self.error_occurred.emit(message)
        if self._state_machine.state != PlayerState.ERROR:
            self._state_machine.transition("error")

    def _on_position_changed(self, position: int) -> None:
        self.position_changed.emit(position)

    def _on_duration_changed(self, duration: int) -> None:
        self.duration_changed.emit(duration)
