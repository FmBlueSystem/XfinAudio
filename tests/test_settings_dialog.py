"""Tests for SettingsDialog reset action."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QMessageBox, QPushButton

from xfinaudio.config.settings import AppSettings, ExportSettings, LoudnessSettings
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


def test_settings_dialog_emits_immutable_loudness_controls(qapp: QApplication) -> None:
    original = AppSettings(loudness=LoudnessSettings(enabled=True, target_lufs=-10.0, tolerance_lu=2.0))
    dialog = SettingsDialog(original)
    enabled = dialog.findChild(QCheckBox, "loudness_enabled_checkbox")
    target = dialog.findChild(QDoubleSpinBox, "loudness_target_lufs_spinbox")
    tolerance = dialog.findChild(QDoubleSpinBox, "loudness_tolerance_lu_spinbox")
    assert enabled is not None
    assert target is not None
    assert tolerance is not None
    captured: list[AppSettings] = []
    dialog.settings_changed.connect(captured.append)

    enabled.setChecked(False)
    target.setValue(-14.0)
    tolerance.setValue(1.5)
    dialog.accept()

    assert captured == [AppSettings(loudness=LoudnessSettings(enabled=False, target_lufs=-14.0, tolerance_lu=1.5))]
    assert captured[0] is not original
    assert original.loudness == LoudnessSettings()
