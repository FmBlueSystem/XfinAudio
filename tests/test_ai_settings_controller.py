"""Persistence is the commit point for runtime AI configuration."""

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QWidget

from xfinaudio.ai import nan_client
from xfinaudio.config.settings import AiSettings, AppSettings
from xfinaudio.config.settings_repository import SettingsRepositoryError
from xfinaudio.desktop.settings_controller import SettingsController
from xfinaudio.desktop.settings_dialog import SettingsDialog


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(nan_client.ENABLED_ENV, "0")
    monkeypatch.delenv(nan_client.API_KEY_ENV, raising=False)
    monkeypatch.delenv(nan_client.ENV_FILE_ENV, raising=False)
    monkeypatch.setenv(nan_client.ENDPOINT_ENV, "https://provider.invalid/chat")
    monkeypatch.setenv("HOME", str(tmp_path))


def make_controller(qapp):
    state = [AppSettings()]
    repo, exports, sync, dialogs = Mock(), Mock(), Mock(), []
    parent = QWidget()
    controller = SettingsController(
        settings_getter=lambda: state[0],
        settings_setter=lambda settings: state.__setitem__(0, settings),
        settings_repository=repo,
        export_screen=exports,
        sync_state=sync,
        tr=lambda text: text,
        message_parent=parent,
        dialog_setter=dialogs.append,
    )
    return controller, state, repo, sync, dialogs


def test_successful_save_applies_ai_without_restart_and_can_disable(qapp):
    controller, state, repo, sync, _ = make_controller(qapp)
    before_save = []
    repo.save.side_effect = lambda _: before_save.append(nan_client.is_ai_enabled())
    controller.apply_settings(AppSettings(ai=AiSettings(enabled=True)))
    assert before_save == [False]
    assert state[0].ai.enabled
    assert nan_client.is_ai_enabled()
    controller.apply_settings(AppSettings())
    assert not nan_client.is_ai_enabled()
    assert sync.call_count == 2


def test_failed_save_preserves_runtime_and_saved_preferences(qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    controller, state, repo, _, _ = make_controller(qapp)
    repo.save.side_effect = SettingsRepositoryError("synthetic save failure")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    controller.apply_settings(AppSettings(ai=AiSettings(enabled=True)))
    assert not nan_client.is_ai_enabled()
    assert state == [AppSettings()]


def test_configure_ai_opens_same_settings_dialog_with_ai_focus(qapp, monkeypatch):
    controller, _, _, _, dialogs = make_controller(qapp)
    focused, opened = [], []
    monkeypatch.setattr(SettingsDialog, "focus_ai", lambda self: focused.append(self))
    monkeypatch.setattr(SettingsDialog, "open_dialog", lambda self: opened.append(self))
    controller.open_ai_settings_dialog()
    assert focused == opened == dialogs
    assert len(dialogs) == 1
    dialogs[0].reject()
