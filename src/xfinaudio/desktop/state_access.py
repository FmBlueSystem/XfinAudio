"""Typed current-snapshot/publication boundary for desktop state owners."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from xfinaudio.desktop.app_state import AppState


@dataclass(frozen=True)
class AppStateAccess:
    current: Callable[[], AppState]
    replace: Callable[[AppState], None]

    def update(self, **changes: object) -> AppState:
        """Derive from the current owner, then publish a checked replacement."""
        state = self.current().model_copy(update=changes)
        self.replace(state)
        return state
