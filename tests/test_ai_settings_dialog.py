"""Settings stages AI preferences and invalidates probes on every dismissal."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QCheckBox, QScrollArea

from xfinaudio.ai import nan_client
from xfinaudio.config.settings import AiSettings, AppSettings, LoudnessSettings
from xfinaudio.desktop.settings_dialog import SettingsDialog


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.delenv(nan_client.ENABLED_ENV, raising=False)
    monkeypatch.delenv(nan_client.API_KEY_ENV, raising=False)
    monkeypatch.delenv(nan_client.ENV_FILE_ENV, raising=False)
    monkeypatch.setenv(nan_client.ENDPOINT_ENV, "https://provider.invalid/chat")
    monkeypatch.setenv("HOME", str(tmp_path))


def test_dialog_saves_ai_candidate_and_preserves_loudness(qapp):
    settings = AppSettings()
    dialog = SettingsDialog(settings)
    enabled = dialog.findChild(QCheckBox, "ai_enabled_checkbox")
    assert enabled is not None
    enabled.setChecked(True)
    received = []
    dialog.settings_changed.connect(received.append)
    dialog.accept()
    assert received[0].ai == AiSettings(enabled=True)
    assert received[0].loudness == LoudnessSettings()
    assert not settings.ai.enabled
    assert not nan_client.is_ai_enabled(), "the dialog does not change runtime before persistence"


def test_dialog_shows_actual_operator_override_without_modifying_settings(qapp, monkeypatch):
    monkeypatch.setenv(nan_client.ENABLED_ENV, "1")
    monkeypatch.setenv(nan_client.ENV_FILE_ENV, "/operator/config.env")
    dialog = SettingsDialog(AppSettings())
    assert dialog._ai_panel.settings() == AiSettings(enabled=True, env_file=Path("/operator/config.env"))
    dialog.reject()
    assert nan_client.is_ai_enabled()


@pytest.mark.parametrize("dismiss", ["reject", "accept", "reset_to_defaults"])
def test_every_dismissal_invalidates_pending_connection_results(qapp, monkeypatch, dismiss):
    dialog = SettingsDialog(AppSettings())
    cancelled = []
    monkeypatch.setattr(dialog._ai_panel, "cancel_pending", lambda: cancelled.append(True))
    getattr(dialog, dismiss)()
    assert cancelled == [True]


def test_configure_ai_focus_and_scrollable_layout_work_on_small_window(qapp):
    dialog = SettingsDialog(AppSettings())
    dialog.resize(720, 540)
    dialog.show()
    dialog.focus_ai()
    qapp.processEvents()
    scroll = dialog.findChild(QScrollArea, "settings_scroll_area")
    assert scroll is not None
    assert scroll.widgetResizable()
    assert dialog._ai_panel.enabled_checkbox.hasFocus()
    assert dialog._ai_panel.enabled_checkbox.visibleRegion().isEmpty() is False
    dialog.reject()
