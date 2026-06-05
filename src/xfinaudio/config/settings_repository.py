"""JSON persistence for versioned XfinAudio application settings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from xfinaudio.config.settings import AppSettings


class SettingsRepositoryError(Exception):
    """Raised when the app-owned settings file cannot be loaded or saved safely."""


class SettingsRepository:
    """Persist application settings to a caller-provided JSON file path."""

    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path

    def load(self) -> AppSettings:
        """Load settings, returning defaults when the settings file does not exist."""
        if not self.settings_path.exists():
            return AppSettings()

        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SettingsRepositoryError(f"Malformed settings JSON: {self.settings_path}") from exc
        except OSError as exc:
            raise SettingsRepositoryError(f"Unable to read settings file: {self.settings_path}") from exc

        if not isinstance(payload, dict):
            raise SettingsRepositoryError(f"Unsupported settings file shape: {self.settings_path}")

        try:
            return AppSettings.model_validate(payload)
        except ValidationError as exc:
            raise SettingsRepositoryError(f"Unsupported settings file: {self.settings_path}") from exc

    def save(self, settings: AppSettings) -> None:
        """Save settings as deterministic, supportable JSON."""
        payload: dict[str, Any] = settings.model_dump(mode="json")
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise SettingsRepositoryError(f"Unable to write settings file: {self.settings_path}") from exc


__all__ = ["SettingsRepository", "SettingsRepositoryError"]
