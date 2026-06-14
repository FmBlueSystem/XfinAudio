"""Tests for AudioPlayer — Qt wrapper around QMediaPlayer."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.audio_player import AudioPlayer
from xfinaudio.desktop.audio_player_state import PlayerState

FIXTURE_WAV = Path(__file__).with_name("fixtures") / "silence_1s.wav"


def ensure_qapp() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


class TestAudioPlayerConstruction:
    def test_can_construct(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        assert player is not None

    def test_initial_state_is_idle(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        assert player.state == PlayerState.IDLE

    def test_initial_position_is_zero(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        assert player.position == 0

    def test_initial_duration_is_zero(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        assert player.duration == 0


class TestStateChangedSignal:
    def test_load_emits_loading(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        calls: list[PlayerState] = []
        player.state_changed.connect(calls.append)
        calls.clear()
        player.load(str(FIXTURE_WAV))
        assert PlayerState.LOADING in calls


class TestLoadAndPlay:
    def test_load_sets_source(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        player.load(str(FIXTURE_WAV))
        # Source is set internally; we can verify via state transition
        assert player._source_path == str(FIXTURE_WAV)

    def test_play_from_idle_raises(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        with pytest.raises(RuntimeError):
            player.play()

    def test_pause_from_idle_raises(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        with pytest.raises(RuntimeError):
            player.pause()


class TestVolume:
    def test_default_volume(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        assert player.volume == pytest.approx(0.7, abs=0.01)

    def test_set_volume_updates(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        player.set_volume(0.5)
        assert player.volume == pytest.approx(0.5, abs=0.01)

    def test_set_volume_clamps_to_zero(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        player.set_volume(-0.5)
        assert player.volume == pytest.approx(0.0, abs=0.01)

    def test_set_volume_clamps_to_one(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        player.set_volume(1.5)
        assert player.volume == pytest.approx(1.0, abs=0.01)


class TestStop:
    def test_stop_from_idle(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        player.stop()
        assert player.state == PlayerState.IDLE

    def test_stop_resets_position(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        player.stop()
        assert player.position == 0


class TestErrorSignal:
    def test_error_occurred_is_emitted(self) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        ensure_qapp()
        player = AudioPlayer()
        errors: list[str] = []
        player.error_occurred.connect(errors.append)
        # Transition to LOADING first, then simulate error
        player.load(str(FIXTURE_WAV))
        player._on_player_error(QMediaPlayer.Error.ResourceError, "not found")
        assert len(errors) == 1
        assert "not found" in errors[0]


class TestSeek:
    def test_seek_when_loaded_does_not_raise(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        player.load(str(FIXTURE_WAV))
        # Seeking a loaded track should not raise
        player.seek(100)
        # Position may be async; just verify no exception

    def test_seek_when_not_loaded_raises(self) -> None:
        ensure_qapp()
        player = AudioPlayer()
        with pytest.raises(RuntimeError):
            player.seek(100)
