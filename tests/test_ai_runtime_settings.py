"""Runtime settings never manipulate or persist credential values."""

from pathlib import Path

import pytest

from xfinaudio.ai import nan_client
from xfinaudio.ai.runtime_settings import apply_ai_settings, effective_ai_settings
from xfinaudio.config.settings import AiSettings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.delenv(nan_client.ENABLED_ENV, raising=False)
    monkeypatch.delenv(nan_client.ENV_FILE_ENV, raising=False)
    monkeypatch.setenv(nan_client.API_KEY_ENV, "SYNTHETIC-ONLY")
    monkeypatch.setenv("HOME", str(tmp_path))


def test_default_stays_off_and_provider_is_explicit():
    settings = effective_ai_settings(AiSettings())
    assert not settings.enabled
    assert settings.provider == "nan"
    assert "SYNTHETIC" not in settings.model_dump_json()


def test_effective_configuration_reflects_operator_overrides(monkeypatch):
    monkeypatch.setenv(nan_client.ENABLED_ENV, "0")
    monkeypatch.setenv(nan_client.ENV_FILE_ENV, "/operator/key.env")
    original = AiSettings(enabled=True, env_file=Path("/settings/key.env"))
    effective = effective_ai_settings(original)
    assert not effective.enabled
    assert effective.env_file == Path("/operator/key.env")
    assert original.enabled


def test_apply_immediately_enables_disables_and_replaces_path(monkeypatch):
    monkeypatch.setenv(nan_client.ENV_FILE_ENV, "/stale/key.env")
    apply_ai_settings(AiSettings(enabled=True, env_file=Path("/new/key.env")))
    assert nan_client.is_ai_enabled()
    assert effective_ai_settings(AiSettings()).env_file == Path("/new/key.env")
    apply_ai_settings(AiSettings())
    assert not nan_client.is_ai_enabled()
    assert effective_ai_settings(AiSettings()).env_file is None
    import os

    assert os.environ[nan_client.API_KEY_ENV] == "SYNTHETIC-ONLY"


def test_explicit_probe_enable_does_not_change_runtime_state(monkeypatch):
    import io
    import os

    monkeypatch.setenv(nan_client.ENABLED_ENV, "0")
    monkeypatch.setenv(nan_client.ENDPOINT_ENV, "https://provider.invalid/chat")
    sent = []

    def send(request, **kwargs):
        sent.append(request)
        return io.BytesIO(b'{"choices":[{"message":{"content":"OK"}}]}')

    assert nan_client.chat("synthetic", enabled=True, transport=send) == "OK"
    assert len(sent) == 1
    assert os.environ[nan_client.ENABLED_ENV] == "0"
    with pytest.raises(nan_client.NanConfigError):
        nan_client.chat("synthetic", enabled=False, transport=send)
    assert len(sent) == 1
