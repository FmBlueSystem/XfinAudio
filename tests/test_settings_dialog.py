"""Tests for SettingsDialog reset action."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.desktop.settings_dialog import SettingsDialog


def test_settings_dialog_has_reset_button(qapp: QApplication) -> None:
    """The settings dialog exposes a Reset to Defaults button."""
    dialog = SettingsDialog(AppSettings())
    button = dialog.findChild(QPushButton, "reset_to_defaults_button")
    assert button is not None
    assert "reset" in button.text().lower()


def test_reset_button_emits_default_settings(qapp: QApplication, monkeypatch: Any) -> None:
    """Clicking the reset button emits settings_changed with AppSettings defaults."""
    custom = AppSettings(export=ExportSettings(safe_export_folder=Path("/custom")))
    dialog = SettingsDialog(custom)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    captured: list[AppSettings] = []
    dialog.settings_changed.connect(captured.append)

    dialog._reset_to_defaults()

    assert len(captured) == 1
    assert captured[0] == AppSettings()
    assert captured[0].export.safe_export_folder is None
