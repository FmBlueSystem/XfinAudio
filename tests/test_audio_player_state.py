"""Tests for audio player state machine — pure Python, no Qt dependency."""

from __future__ import annotations

import pytest

from xfinaudio.desktop.audio_player_state import PlayerState, PlayerStateMachine


class TestPlayerStateEnum:
    def test_has_idle(self) -> None:
        assert PlayerState.IDLE is not None

    def test_has_loading(self) -> None:
        assert PlayerState.LOADING is not None

    def test_has_playing(self) -> None:
        assert PlayerState.PLAYING is not None

    def test_has_paused(self) -> None:
        assert PlayerState.PAUSED is not None

    def test_has_error(self) -> None:
        assert PlayerState.ERROR is not None


class TestPlayerStateMachineDefaults:
    def test_initial_state_is_idle(self) -> None:
        sm = PlayerStateMachine()
        assert sm.state == PlayerState.IDLE

    def test_initial_state_is_not_playing(self) -> None:
        sm = PlayerStateMachine()
        assert sm.state != PlayerState.PLAYING


class TestValidTransitions:
    def test_idle_to_loading(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        assert sm.state == PlayerState.LOADING

    def test_loading_to_playing(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("play")
        assert sm.state == PlayerState.PLAYING

    def test_playing_to_paused(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("play")
        sm.transition("pause")
        assert sm.state == PlayerState.PAUSED

    def test_paused_to_playing(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("play")
        sm.transition("pause")
        sm.transition("play")
        assert sm.state == PlayerState.PLAYING

    def test_playing_to_idle(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("play")
        sm.transition("stop")
        assert sm.state == PlayerState.IDLE

    def test_paused_to_idle(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("play")
        sm.transition("pause")
        sm.transition("stop")
        assert sm.state == PlayerState.IDLE

    def test_loading_to_idle(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("stop")
        assert sm.state == PlayerState.IDLE

    def test_error_to_idle(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("error")
        assert sm.state == PlayerState.ERROR
        sm.transition("stop")
        assert sm.state == PlayerState.IDLE

    def test_idle_to_idle_is_noop(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("stop")
        assert sm.state == PlayerState.IDLE


class TestInvalidTransitions:
    def test_idle_to_playing_raises(self) -> None:
        sm = PlayerStateMachine()
        with pytest.raises(ValueError):
            sm.transition("play")

    def test_idle_to_pause_raises(self) -> None:
        sm = PlayerStateMachine()
        with pytest.raises(ValueError):
            sm.transition("pause")

    def test_playing_to_loading_raises(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("play")
        with pytest.raises(ValueError):
            sm.transition("load")

    def test_error_to_playing_raises(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("error")
        with pytest.raises(ValueError):
            sm.transition("play")

    def test_paused_to_loading_raises(self) -> None:
        sm = PlayerStateMachine()
        sm.transition("load")
        sm.transition("play")
        sm.transition("pause")
        with pytest.raises(ValueError):
            sm.transition("load")


class TestCallback:
    def test_callback_invoked_on_transition(self) -> None:
        calls: list[tuple[PlayerState, PlayerState, str]] = []

        def on_transition(old: PlayerState, new: PlayerState, event: str) -> None:
            calls.append((old, new, event))

        sm = PlayerStateMachine(on_transition=on_transition)
        sm.transition("load")
        assert len(calls) == 1
        assert calls[0] == (PlayerState.IDLE, PlayerState.LOADING, "load")

    def test_callback_not_invoked_on_invalid_transition(self) -> None:
        calls: list[tuple[PlayerState, PlayerState, str]] = []

        def on_transition(old: PlayerState, new: PlayerState, event: str) -> None:
            calls.append((old, new, event))

        sm = PlayerStateMachine(on_transition=on_transition)
        with pytest.raises(ValueError):
            sm.transition("play")
        assert calls == []
