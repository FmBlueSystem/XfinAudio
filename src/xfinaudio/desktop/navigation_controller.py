"""Navigation rules for the XfinAudio DJ flow."""

from __future__ import annotations

from typing import cast

from xfinaudio.desktop.app_state import AppState, ScreenName

SCREEN_ORDER: list[str] = ["library", "build", "review", "export"]
# "metadata" is always accessible but lives outside the linear flow.


class NavigationController:
    """Encapsulates the navigation rules of the DJ flow."""

    def can_go_to(self, screen: str, state: AppState) -> bool:
        """Return True if the transition to *screen* is valid given *state*."""
        if screen in ("library", "metadata"):
            return True

        if screen == "build":
            return len(state.scanned_records) > 0 and not state.is_scanning

        if screen == "review":
            return state.last_recommendation is not None and not state.is_recommending

        if screen == "export":
            if state.is_recommending:
                return False
            if state.last_recommendation is None:
                return False
            if state.last_dj_readiness_report is None:
                return False
            return state.last_dj_readiness_report.status != "blocked"

        # Unknown screen — deny by default.
        return False

    def go_to(self, screen: str, state: AppState) -> AppState:
        """Return a new AppState with *current_screen* set, or the same state if the transition is invalid."""
        if not self.can_go_to(screen, state):
            return state
        return state.with_screen(cast(ScreenName, screen))

    def next_screen(self, state: AppState) -> str | None:
        """Return the next reachable screen in the linear flow, or None."""
        if state.current_screen == "metadata":
            return None

        current = state.current_screen
        if current not in SCREEN_ORDER:
            return None

        idx = SCREEN_ORDER.index(current)
        for candidate in SCREEN_ORDER[idx + 1 :]:
            if self.can_go_to(candidate, state):
                return candidate

        return None

    def back_screen(self, state: AppState) -> str | None:
        """Return the previous screen in the linear flow, or None."""
        if state.is_scanning or state.is_recommending:
            return None

        current = state.current_screen
        if current in ("library", "metadata"):
            return None

        if current not in SCREEN_ORDER:
            return None

        idx = SCREEN_ORDER.index(current)
        if idx == 0:
            return None

        return SCREEN_ORDER[idx - 1]


__all__ = ["SCREEN_ORDER", "NavigationController"]
