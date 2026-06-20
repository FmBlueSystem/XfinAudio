"""Ports for settings persistence."""

from __future__ import annotations

from typing import Protocol

from xfinaudio.config.settings import AppSettings


class SettingsRepositoryPort(Protocol):
    """Persistence boundary for application settings."""

    def load(self) -> AppSettings:
        """Load persisted settings or defaults."""
        ...

    def save(self, settings: AppSettings) -> None:
        """Persist application settings."""
        ...
