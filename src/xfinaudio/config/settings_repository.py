"""JSON persistence for versioned XfinAudio application settings."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from xfinaudio.config.settings import AppSettings


class SettingsRepositoryError(Exception):
    """Raised when the app-owned settings file cannot be loaded or saved safely."""


class InvalidSettingsError(SettingsRepositoryError):
    """The file was readable, but its contents cannot be used."""


class SettingsRepository:
    """Persist application settings to a caller-provided JSON file path."""

    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path
        self.recovery_warning: str | None = None

    def load(self) -> AppSettings:
        """Load settings, returning defaults when the settings file does not exist."""
        if not self.settings_path.exists():
            return AppSettings()

        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidSettingsError(f"Malformed settings JSON: {self.settings_path}") from exc
        except OSError as exc:
            raise SettingsRepositoryError(f"Unable to read settings file: {self.settings_path}") from exc

        if not isinstance(payload, dict):
            raise InvalidSettingsError(f"Unsupported settings file shape: {self.settings_path}")

        try:
            return AppSettings.model_validate(payload)
        except ValidationError as exc:
            raise InvalidSettingsError(f"Unsupported settings file: {self.settings_path}") from exc

    def load_with_recovery(self) -> AppSettings:
        """Preserve invalid settings before returning defaults for desktop recovery."""
        self.recovery_warning = None
        try:
            return self.load()
        except InvalidSettingsError:
            recovery_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=self.settings_path.parent,
                    prefix=f"{self.settings_path.name}.recovery-",
                    delete=False,
                ) as recovery:
                    recovery_path = Path(recovery.name)
                os.replace(self.settings_path, recovery_path)
            except OSError as exc:
                if recovery_path is not None:
                    with suppress(OSError):
                        recovery_path.unlink(missing_ok=True)
                raise SettingsRepositoryError(f"Unable to preserve invalid settings: {self.settings_path}") from exc
            self.recovery_warning = (
                f"Settings could not be loaded; original preserved at {recovery_path}. "
                "Loudness write-back is paused. Open Settings to review your preferences."
            )
            defaults = AppSettings()
            return defaults.model_copy(update={"loudness": defaults.loudness.model_copy(update={"enabled": False})})

    def save(self, settings: AppSettings) -> None:
        """Save settings as deterministic, supportable JSON."""
        payload: dict[str, Any] = settings.model_dump(mode="json")
        serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        temporary_path: Path | None = None
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.settings_path.parent,
                prefix=f".{self.settings_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.settings_path)
        except OSError as exc:
            raise SettingsRepositoryError(f"Unable to write settings file: {self.settings_path}") from exc
        finally:
            if temporary_path is not None:
                with suppress(OSError):
                    temporary_path.unlink(missing_ok=True)


__all__ = ["SettingsRepository", "SettingsRepositoryError"]
