"""Visible recovery and failed-save settings regressions."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from xfinaudio.config.settings import AppSettings, LoudnessSettings
from xfinaudio.config.settings_repository import SettingsRepositoryError
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.settings_controller import SettingsController


def test_startup_recovers_invalid_settings_with_visible_diagnostic(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "settings.json"
    path.write_text("{broken")
    window = MainWindow.with_defaults(tmp_path / "library.db", path)
    assert "preserved" in window.statusBar().currentMessage()
    assert "recovery-" in window.statusBar().currentMessage()
    window.close()
    app.processEvents()


@pytest.mark.parametrize("action", ["dialog", "spectral"])
def test_save_failure_keeps_active_settings_and_warns(monkeypatch, action):
    initial = AppSettings()
    setter, warning, sync = MagicMock(), MagicMock(), MagicMock()
    repository = MagicMock()
    repository.save.side_effect = SettingsRepositoryError("synthetic disk full")
    monkeypatch.setattr("xfinaudio.desktop.settings_controller.QMessageBox.warning", warning)
    controller = SettingsController(
        settings_getter=lambda: initial,
        settings_setter=setter,
        settings_repository=repository,
        export_screen=MagicMock(),
        sync_state=sync,
        tr=lambda text: text,
        message_parent=MagicMock(),
        dialog_setter=MagicMock(),
    )
    if action == "dialog":
        controller.apply_settings(initial.model_copy(update={"loudness": LoudnessSettings(enabled=False)}))
    else:
        controller.on_spectral_cohesion_changed(75)
    setter.assert_not_called()
    warning.assert_called_once()
    sync.assert_called_once()
