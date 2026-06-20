"""Desktop application entrypoint."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.i18n import install_translator
from xfinaudio.desktop.main_window import MainWindow


def _set_process_name(name: str) -> None:
    """Set the OS-visible process name.

    On macOS this affects the system menu bar label; on Linux it updates
    /proc/PID/comm.  Must be called before QApplication is created.
    """
    try:
        import setproctitle

        setproctitle.setproctitle(name)
    except Exception:
        pass


def _configure_macos_app(name: str, icon_path: Path | None) -> None:
    """Configure macOS-specific app identity (dock icon + menu bar name).

    Uses PyObjC when available.  Safe to call on non-macOS platforms.
    """
    if sys.platform != "darwin":
        return

    try:
        from Foundation import NSBundle

        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info is not None:
            info["CFBundleName"] = name
            info["CFBundleDisplayName"] = name
    except Exception:
        pass

    try:
        from AppKit import NSApplication, NSImage

        nsapp = NSApplication.sharedApplication()
        if icon_path is not None and icon_path.exists():
            image = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
            if image is not None:
                nsapp.setApplicationIconImage_(image)
    except Exception:
        pass


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


def _load_settings_language() -> str | None:
    """Return the saved UI language preference, or None if not set."""
    try:
        from xfinaudio.config.settings_repository import SettingsRepository

        repo = SettingsRepository(settings_path_from_environment())
        settings = repo.load()
        return settings.ui.language or None
    except Exception:
        return None


def main() -> int:
    """Start the XfinAudio desktop application."""
    sys.argv[0] = "XfinAudio"
    _set_process_name("XfinAudio")
    app = QApplication(sys.argv)
    app.setApplicationName("XfinAudio")
    app.setApplicationDisplayName("XfinAudio")
    icon_path = Path(__file__).resolve().parents[2] / "assets" / "icons" / "app-icon-512x512.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    _configure_macos_app("XfinAudio", icon_path)
    lang = os.environ.get("XFINAUDIO_LANG") or _load_settings_language()
    install_translator(lang)
    if package_smoke_enabled():
        return 0
    window = MainWindow.with_defaults(database_path_from_environment(), settings_path_from_environment())
    window.showMaximized()
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
