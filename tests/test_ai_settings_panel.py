"""The AI control surface stays explicit, secret-free and reversible."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog, QLineEdit

from xfinaudio.ai import nan_client
from xfinaudio.ai.connection_test import ConnectionStatus
from xfinaudio.config.settings import AiSettings
from xfinaudio.desktop.ai_settings_panel import AiSettingsPanel


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.delenv(nan_client.API_KEY_ENV, raising=False)
    monkeypatch.delenv(nan_client.ENV_FILE_ENV, raising=False)
    monkeypatch.setenv(nan_client.ENDPOINT_ENV, "https://provider.invalid/chat")
    monkeypatch.setenv("HOME", str(tmp_path))


def test_default_panel_has_disclosures_no_key_field_and_no_request(qapp):
    panel = AiSettingsPanel(AiSettings())
    assert not panel.enabled_checkbox.isChecked()
    assert panel.provider_combo.currentData() == "nan"
    assert "disabled" in panel.status_label.text().lower()
    assert not panel.test_button.isEnabled()
    assert not panel.findChildren(QLineEdit)
    assert "never audio" in panel.privacy_label.text().lower()
    assert "provider.invalid" in panel.privacy_label.text()
    assert "Reply with OK. XfinAudio connection test." in panel.test_disclosure.text()
    assert "quota" in panel.test_disclosure.text()
    assert "outside" in panel.guidance_label.text()
    assert not panel._probe.busy


def test_controls_change_only_immutable_candidate_and_file_path(qapp, monkeypatch, tmp_path):
    original = AiSettings()
    panel = AiSettingsPanel(original)
    path = tmp_path / "operator.env"
    path.write_text("SYNTHETIC-SECRET")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(path), ""))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("UI read credential contents"))
    panel.choose_button.click()
    panel.enabled_checkbox.setChecked(True)
    candidate = panel.settings()
    assert candidate.enabled and candidate.env_file == path
    assert original == AiSettings()
    assert panel.test_button.isEnabled()
    assert "not tested" in panel.status_label.text()
    assert "SYNTHETIC-SECRET" not in candidate.model_dump_json()
    panel.default_button.click()
    assert panel.settings().env_file is None
    assert "Credential not found" in panel.status_label.text()
    assert not panel.test_button.isEnabled()


def test_cancelled_file_chooser_preserves_path(qapp, monkeypatch):
    panel = AiSettingsPanel(AiSettings(env_file=Path("/existing.env")))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    panel.choose_button.click()
    assert panel.settings().env_file == Path("/existing.env")


def test_test_result_and_configuration_change_clear_stale_status(qapp, monkeypatch):
    monkeypatch.setenv(nan_client.API_KEY_ENV, "SYNTHETIC-SECRET")
    panel = AiSettingsPanel(AiSettings(enabled=True))
    calls = []
    monkeypatch.setattr(panel._probe, "start", lambda settings: calls.append(settings) or True)
    panel.test_button.click()
    assert calls == [AiSettings(enabled=True)]
    panel._probe.completed.emit(ConnectionStatus("connected", "Connection successful."))
    assert "successful" in panel.status_label.text()
    panel.enabled_checkbox.setChecked(False)
    assert "disabled" in panel.status_label.text().lower()
    assert not panel.test_button.isEnabled()


def test_cancel_is_honest_about_sent_request_and_never_saves(qapp):
    panel = AiSettingsPanel(AiSettings())
    panel.cancel_pending()
    panel._cancel_test()
    assert "already sent" in panel.status_label.text()
    assert "retry" in panel.status_label.text().lower()
