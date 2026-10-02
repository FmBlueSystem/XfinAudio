"""All connection probes use fake transport and synthetic credentials."""

import io
import json
import urllib.error
from email.message import Message

import pytest

from xfinaudio.ai import nan_client
from xfinaudio.ai.connection_test import PROBE_MESSAGE, configuration_status, endpoint_label, run_connection_test
from xfinaudio.config.settings import AiSettings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(nan_client.ENABLED_ENV, "0")
    monkeypatch.setenv(nan_client.API_KEY_ENV, "SYNTHETIC-SECRET")
    monkeypatch.setenv(nan_client.ENDPOINT_ENV, "https://provider.invalid/chat")
    monkeypatch.setenv(nan_client.ENV_FILE_ENV, str(tmp_path / "absent.env"))
    monkeypatch.setenv("HOME", str(tmp_path))


def test_status_is_offline_by_default_without_reading_credentials(monkeypatch):
    monkeypatch.setattr(nan_client, "load_api_key_from_env_file", lambda _: pytest.fail("credential read"))
    assert configuration_status(AiSettings()).state == "disabled"
    assert configuration_status(AiSettings(enabled=True)).state == "untested"
    assert endpoint_label() == "provider.invalid"


def test_missing_key_and_invalid_endpoint_never_call_transport(monkeypatch):
    def send(*args, **kwargs):
        pytest.fail("unexpected transmission")

    monkeypatch.delenv(nan_client.API_KEY_ENV)
    assert run_connection_test(AiSettings(enabled=True), transport=send).state == "missing_key"
    assert run_connection_test(AiSettings(), transport=send).state == "disabled"
    monkeypatch.setenv(nan_client.ENDPOINT_ENV, "http://unsafe.invalid/chat")
    assert configuration_status(AiSettings(enabled=True)).state == "invalid_configuration"
    assert endpoint_label() == "Invalid HTTPS endpoint"


def test_probe_discloses_and_sends_only_fixed_content_without_enabling_runtime():
    sent = []

    def send(request, **kwargs):
        sent.append((request, kwargs))
        return io.BytesIO(b'{"choices":[{"message":{"content":"arbitrary-provider-response"}}]}')

    result = run_connection_test(AiSettings(enabled=True), transport=send)
    assert result.state == "connected"
    assert "arbitrary-provider-response" not in result.message
    assert not nan_client.is_ai_enabled()
    request, options = sent[0]
    assert json.loads(request.data)["messages"] == [{"role": "user", "content": PROBE_MESSAGE}]
    assert options["timeout"] == 10.0
    assert request.get_header("Authorization") == "Bearer SYNTHETIC-SECRET"


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (
            urllib.error.HTTPError("https://provider.invalid", 401, "SYNTHETIC-SECRET", Message(), None),
            "authentication_failed",
        ),
        (urllib.error.URLError("SYNTHETIC-SECRET"), "unavailable"),
        (TimeoutError("SYNTHETIC-SECRET"), "unavailable"),
        (ValueError("SYNTHETIC-SECRET"), "invalid_configuration"),
    ],
)
def test_failure_is_safe_and_retry_succeeds(failure, expected):
    def send(*args, **kwargs):
        raise failure

    result = run_connection_test(AiSettings(enabled=True), transport=send)
    assert result.state == expected
    assert "SYNTHETIC-SECRET" not in result.message
    result = run_connection_test(
        AiSettings(enabled=True),
        transport=lambda *args, **kwargs: io.BytesIO(b'{"choices":[{"message":{"content":"OK"}}]}'),
    )
    assert result.state == "connected"


def test_malformed_response_is_not_success():
    result = run_connection_test(AiSettings(enabled=True), transport=lambda *args, **kwargs: io.BytesIO(b"invalid"))
    assert result.state == "invalid_response"


def test_file_presence_is_not_claimed_as_valid_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv(nan_client.API_KEY_ENV)
    path = tmp_path / "empty.env"
    path.write_text("")
    settings = AiSettings(enabled=True, env_file=path)
    assert configuration_status(settings).state == "untested"
    result = run_connection_test(settings, transport=lambda *args, **kwargs: pytest.fail("unexpected transmission"))
    assert result.state == "invalid_configuration"


def test_environment_key_precedence_does_not_require_access_to_file(monkeypatch):
    from pathlib import Path

    def denied_stat(*args, **kwargs):
        raise OSError("synthetic inaccessible path")

    monkeypatch.setattr(Path, "is_file", denied_stat)
    assert configuration_status(AiSettings(enabled=True)).state == "untested"
