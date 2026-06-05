"""Desktop application entrypoint."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow


def default_database_path() -> Path:
    """Return the application-controlled SQLite database path."""
    return Path.home() / ".xfinaudio" / "xfinaudio.sqlite3"


def default_settings_path() -> Path:
    """Return the application-controlled JSON settings path."""
    return Path.home() / ".xfinaudio" / "settings.json"


def package_smoke_enabled() -> bool:
    """Return whether the desktop app should exit after smoke initialization."""
    return os.environ.get("XFINAUDIO_PACKAGE_SMOKE") == "1"


def database_path_from_environment() -> Path:
    """Return the configured database path, honoring packaging smoke overrides."""
    override = os.environ.get("XFINAUDIO_DB_PATH")
    if override:
        return Path(override)
    return default_database_path()


def settings_path_from_environment() -> Path:
    """Return the configured settings path, honoring packaging smoke overrides."""
    override = os.environ.get("XFINAUDIO_SETTINGS_PATH")
    if override:
        return Path(override)
    return default_settings_path()


def main() -> int:
    """Start the XfinAudio desktop application."""
    app = QApplication(sys.argv)
    window = MainWindow.with_defaults(database_path_from_environment(), settings_path_from_environment())
    window.resize(1000, 600)
    if package_smoke_enabled():
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
