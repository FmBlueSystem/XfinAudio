"""Pure-Python audio player state machine.

No Qt dependency — suitable for business logic and unit testing.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto


class PlayerState(Enum):
    """Discrete states for the audio preview player."""

    IDLE = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()
    ERROR = auto()


class PlayerStateMachine:
    """Deterministic state machine for audio player lifecycle.

    All valid transitions are declared explicitly; any other transition
    raises ``ValueError``.
    """

    _TRANSITIONS: dict[PlayerState, dict[str, PlayerState]] = {
        PlayerState.IDLE: {
            "load": PlayerState.LOADING,
            "stop": PlayerState.IDLE,
        },
        PlayerState.LOADING: {
            "play": PlayerState.PLAYING,
            "error": PlayerState.ERROR,
            "stop": PlayerState.IDLE,
        },
        PlayerState.PLAYING: {
            "pause": PlayerState.PAUSED,
            "stop": PlayerState.IDLE,
        },
        PlayerState.PAUSED: {
            "play": PlayerState.PLAYING,
            "stop": PlayerState.IDLE,
        },
        PlayerState.ERROR: {
            "stop": PlayerState.IDLE,
        },
    }

    def __init__(
        self,
        on_transition: Callable[[PlayerState, PlayerState, str], None] | None = None,
    ) -> None:
        self._state = PlayerState.IDLE
        self._on_transition = on_transition

    @property
    def state(self) -> PlayerState:
        return self._state

    def transition(self, event: str) -> None:
        """Attempt to transition via *event*.

        Raises:
            ValueError: If the current state does not accept *event*.
        """
        transitions = self._TRANSITIONS.get(self._state, {})
        if event not in transitions:
            raise ValueError(f"Invalid transition '{event}' from state {self._state.name}")
        new_state = transitions[event]
        if self._on_transition is not None:
            self._on_transition(self._state, new_state, event)
        self._state = new_state
