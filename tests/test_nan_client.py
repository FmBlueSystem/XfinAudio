"""Offline contract tests for the Nan Builders adapter (Fase 0 spike).

Every test injects a fake transport, so the suite never opens a socket and never
needs a real ``NAN_API_KEY``. The fake records the outgoing request so the
payload, endpoint, headers and timeout stay pinned by assertions.
"""

from __future__ import annotations

import io
import json
import traceback
import urllib.error
import urllib.request
from collections.abc import Callable
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from xfinaudio.ai import (
    NanConfigError,
    NanRequestError,
    chat,
    default_env_file_path,
    is_ai_enabled,
    load_api_key_from_env_file,
)

API_KEY = "nan-key-value-that-must-never-leak"
FILE_KEY = "nan-file-key-value-that-must-never-leak"
CONFIGURED_ENDPOINT = "https://example.test/v1/chat/completions"
OFFICIAL_ENDPOINT = "https://api.nan.builders/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"


class FakeResponse:
    """Minimal stand-in for the object ``urlopen`` returns."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class FakeTransport:
    """Record the request and either return a body or raise the queued failure."""

    def __init__(self, result: bytes | BaseException) -> None:
        self.result = result
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[float | None] = []

    def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if isinstance(self.result, BaseException):
            raise self.result
        return FakeResponse(self.result)

    @property
    def request(self) -> urllib.request.Request:
        assert self.requests, "the transport was never called"
        return self.requests[0]


def completion_body(content: str, model: str = DEFAULT_MODEL) -> bytes:
    payload = {
        "id": "chatcmpl-test",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
    }
    return json.dumps(payload).encode("utf-8")


def payload_of(transport: FakeTransport) -> dict[str, Any]:
    data = transport.request.data
    assert data is not None, "the request carried no body"
    decoded = json.loads(data.decode("utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def header_of(request: urllib.request.Request, name: str) -> str | None:
    """Read a header case-insensitively: urllib stores ``Content-Type`` as ``Content-type``."""
    for key, value in request.header_items():
        if key.lower() == name.lower():
            return value
    return None


def http_unauthorized() -> BaseException:
    headers: Message[str, str] = Message()
    return urllib.error.HTTPError(CONFIGURED_ENDPOINT, 401, "Unauthorized", headers, None)


def socket_timeout() -> BaseException:
    # `socket.timeout` is a deprecated alias of the builtin TimeoutError, which
    # is what urlopen raises (directly or wrapped) when a read times out.
    return TimeoutError("timed out")


def url_error_wrapping_timeout() -> BaseException:
    return urllib.error.URLError(TimeoutError("timed out"))


def connection_refused() -> BaseException:
    return urllib.error.URLError(OSError("Connection refused"))


@pytest.fixture
def ai_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Enable the flag, provide a key, and clear ambient Nan overrides.

    The env-file fallback points at a path inside ``tmp_path`` that does not
    exist, so no test can ever read the operator's real ``~/.xfinaudio/apiIA.env``.
    """
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", API_KEY)
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent-from-fixture.env"))
    monkeypatch.delenv("NAN_API_BASE", raising=False)
    monkeypatch.delenv("NAN_MODEL", raising=False)


def test_ai_flag_is_off_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XFINAUDIO_AI_ENABLED", raising=False)

    assert is_ai_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "TRUE", "True", "YeS"])
def test_ai_flag_accepts_every_truthy_spelling(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", value)

    assert is_ai_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "enabled"])
def test_ai_flag_is_off_for_every_other_value(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", value)

    assert is_ai_enabled() is False


def test_chat_without_api_key_names_the_env_var(monkeypatch: pytest.MonkeyPatch, ai_env: None) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    transport = FakeTransport(completion_body("unused"))

    with pytest.raises(NanConfigError) as excinfo:
        chat("hi", transport=transport)

    message = str(excinfo.value)
    assert "NAN_API_KEY" in message
    assert "export" in message
    assert transport.requests == [], "config errors must fail before any transport call"


def test_chat_refuses_to_run_while_the_flag_is_off(monkeypatch: pytest.MonkeyPatch, ai_env: None) -> None:
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    transport = FakeTransport(completion_body("unused"))

    with pytest.raises(NanConfigError) as excinfo:
        chat("hi", transport=transport)

    assert "XFINAUDIO_AI_ENABLED" in str(excinfo.value)
    assert transport.requests == [], "a disabled adapter must never reach the transport"


def test_chat_posts_the_openai_payload_to_the_configured_endpoint(
    monkeypatch: pytest.MonkeyPatch, ai_env: None
) -> None:
    monkeypatch.setenv("NAN_API_BASE", CONFIGURED_ENDPOINT)
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    request = transport.request
    assert request.full_url == CONFIGURED_ENDPOINT
    assert request.get_method() == "POST"
    assert header_of(request, "Content-Type") == "application/json"
    assert payload_of(transport) == {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": "hi"}],
    }


def test_chat_uses_the_official_endpoint_by_default(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert transport.request.full_url == OFFICIAL_ENDPOINT


def test_chat_sends_the_system_message_before_the_user_message(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("explain the transition", system="You are a senior DJ assistant.", transport=transport)

    assert payload_of(transport)["messages"] == [
        {"role": "system", "content": "You are a senior DJ assistant."},
        {"role": "user", "content": "explain the transition"},
    ]


def test_chat_without_messages_keeps_the_request_body_byte_identical(ai_env: None) -> None:
    # Pins today's serialization exactly: adding the optional ``messages``
    # keyword must not change the bytes of a single-message request.
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert transport.request.data == (
        b'{"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": "hi"}]}'
    )

    with_system = FakeTransport(completion_body("ok"))

    chat("hi", system="S", transport=with_system)

    assert with_system.request.data == (
        b'{"model": "deepseek-v4-flash", "messages": [{"role": "system", "content": "S"}, '
        b'{"role": "user", "content": "hi"}]}'
    )


CONVERSATION = [
    {"role": "system", "content": "Eres un asistente de listas."},
    {"role": "user", "content": "¿Qué pista quitarías?"},
    {"role": "assistant", "content": "Quitaría la 4."},
    {"role": "user", "content": "¿Por qué?"},
]


def test_chat_sends_exactly_the_given_conversation_in_order(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("unused request text", system="unused system", messages=tuple(CONVERSATION), transport=transport)

    assert payload_of(transport)["messages"] == CONVERSATION


@pytest.mark.parametrize(
    "messages",
    [
        pytest.param([], id="empty-list"),
        pytest.param([{"role": "tool", "content": "hi"}], id="role-outside-the-three"),
        pytest.param([{"role": "USER", "content": "hi"}], id="role-wrong-case"),
        pytest.param([{"role": "", "content": "hi"}], id="role-empty"),
        pytest.param([{"role": None, "content": "hi"}], id="role-not-a-string"),
        pytest.param([{"role": "user", "content": ""}], id="content-empty"),
        pytest.param([{"role": "user", "content": "   "}], id="content-blank"),
        pytest.param([{"role": "user", "content": None}], id="content-not-a-string"),
        pytest.param([{"role": "user"}], id="missing-content"),
        pytest.param([{"content": "hi"}], id="missing-role"),
        pytest.param([{"role": "user", "content": "hi", "name": "x"}], id="unexpected-key"),
        pytest.param(["hi"], id="entry-is-not-a-mapping"),
        pytest.param("hi", id="not-a-sequence-of-messages"),
        pytest.param(
            [{"role": "user", "content": "hi"}, {"role": "assistant", "content": ""}], id="later-message-invalid"
        ),
    ],
)
def test_chat_rejects_invalid_messages_before_any_network_call(ai_env: None, messages: Any) -> None:
    transport = FakeTransport(completion_body("unused"))

    with pytest.raises(ValueError) as excinfo:
        chat("hi", messages=messages, transport=transport)

    assert excinfo.type is ValueError
    assert "message" in str(excinfo.value).lower()
    assert transport.requests == [], "an invalid conversation must fail before any transport call"


def test_chat_sends_the_bearer_authorization_header(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert header_of(transport.request, "Authorization") == f"Bearer {API_KEY}"


def test_chat_sends_the_app_user_agent(ai_env: None) -> None:
    # The Nan CDN rejects the default Python-urllib agent with HTTP 403.
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    user_agent = header_of(transport.request, "User-Agent")
    assert user_agent
    assert "python" not in user_agent.lower()


def test_chat_passes_the_default_timeout_to_the_transport(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert transport.timeouts == [30.0]


def test_chat_passes_an_explicit_timeout_to_the_transport(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("hi", timeout=2.5, transport=transport)

    assert transport.timeouts == [2.5]


def test_chat_returns_the_assistant_content(ai_env: None) -> None:
    transport = FakeTransport(completion_body("hello from Nan"))

    assert chat("hi", transport=transport) == "hello from Nan"


def test_chat_rejects_a_body_that_is_not_json(ai_env: None) -> None:
    transport = FakeTransport(b"<html>gateway error</html>")

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", transport=transport)

    assert "JSON" in str(excinfo.value)


@pytest.mark.parametrize(
    "body",
    [
        {"choices": []},
        {"choices": [{"message": {"role": "assistant"}}]},
        {"choices": [{"message": {"role": "assistant", "content": None}}]},
    ],
)
def test_chat_rejects_a_body_without_usable_content(ai_env: None, body: dict[str, Any]) -> None:
    transport = FakeTransport(json.dumps(body).encode("utf-8"))

    with pytest.raises(NanRequestError):
        chat("hi", transport=transport)


def test_chat_wraps_http_errors(ai_env: None) -> None:
    transport = FakeTransport(http_unauthorized())

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", transport=transport)

    assert "401" in str(excinfo.value)


@pytest.mark.parametrize("failure", [socket_timeout, url_error_wrapping_timeout])
def test_chat_wraps_timeouts(ai_env: None, failure: Callable[[], BaseException]) -> None:
    transport = FakeTransport(failure())

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", timeout=1.5, transport=transport)

    assert "timed out" in str(excinfo.value)


def test_chat_wraps_connection_errors(ai_env: None) -> None:
    transport = FakeTransport(connection_refused())

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", transport=transport)

    assert "Connection refused" in str(excinfo.value)


@pytest.mark.parametrize("failure", [http_unauthorized, socket_timeout, url_error_wrapping_timeout, connection_refused])
def test_chat_error_text_never_carries_the_api_key(ai_env: None, failure: Callable[[], BaseException]) -> None:
    transport = FakeTransport(failure())

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", transport=transport)

    error = excinfo.value
    rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    assert API_KEY not in str(error)
    assert API_KEY not in repr(error)
    assert API_KEY not in rendered


def test_chat_requires_the_flag_and_key_error_text_never_carries_the_api_key(
    monkeypatch: pytest.MonkeyPatch, ai_env: None
) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)

    with pytest.raises(NanConfigError) as excinfo:
        chat("hi", transport=FakeTransport(completion_body("unused")))

    error = excinfo.value
    rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    assert API_KEY not in rendered


def test_chat_model_defaults_to_the_subscription_default(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert payload_of(transport)["model"] == "deepseek-v4-flash"


def test_chat_model_comes_from_the_nan_model_env(monkeypatch: pytest.MonkeyPatch, ai_env: None) -> None:
    monkeypatch.setenv("NAN_MODEL", "qwen3.6")
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert payload_of(transport)["model"] == "qwen3.6"


def test_chat_model_parameter_beats_the_nan_model_env(monkeypatch: pytest.MonkeyPatch, ai_env: None) -> None:
    monkeypatch.setenv("NAN_MODEL", "qwen3.6")
    transport = FakeTransport(completion_body("ok"))

    chat("hi", model="glm5.3-flash", transport=transport)

    assert payload_of(transport)["model"] == "glm5.3-flash"


def test_chat_model_comes_from_the_explicit_request_context(monkeypatch: pytest.MonkeyPatch, ai_env: None) -> None:
    """S11: the app binds the chosen model explicitly, and it beats NAN_MODEL and the argument."""
    from xfinaudio.ai.nan_client import request_context

    monkeypatch.setenv("NAN_MODEL", "mimo-v2.5")
    for model in ("deepseek-v4-flash", "glm5.3-flash", "qwen3.6"):
        transport = FakeTransport(completion_body("ok"))

        with request_context(enabled=True, key_provider=lambda: API_KEY, model=model):
            chat("hi", model="mimo-v2.5", transport=transport)

        assert payload_of(transport)["model"] == model
        assert transport.request.full_url == OFFICIAL_ENDPOINT


def write_env_file(tmp_path: Path, content: str, name: str = "apiIA.env") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_env_file_accepts_a_bare_key_line(tmp_path: Path) -> None:
    path = write_env_file(tmp_path, f"  {FILE_KEY}\n")

    assert load_api_key_from_env_file(path) == FILE_KEY


def test_env_file_accepts_dotenv_style_content(tmp_path: Path) -> None:
    path = write_env_file(
        tmp_path,
        f'# Nan Builders subscription key\n\nNAN_MODEL=qwen3.6\n  NAN_API_KEY = "{FILE_KEY}"  \n',
    )

    assert load_api_key_from_env_file(path) == FILE_KEY


def test_env_file_named_entry_beats_a_bare_line(tmp_path: Path) -> None:
    path = write_env_file(tmp_path, f"bare-value\nNAN_API_KEY={FILE_KEY}\n")

    assert load_api_key_from_env_file(path) == FILE_KEY


@pytest.mark.parametrize("content", ["", "\n\n", "# only a comment\n", "NAN_MODEL=qwen3.6\n", "OTHER_KEY=\n"])
def test_env_file_without_a_key_raises_naming_the_path(tmp_path: Path, content: str) -> None:
    path = write_env_file(tmp_path, content)

    with pytest.raises(NanConfigError) as excinfo:
        load_api_key_from_env_file(path)

    message = str(excinfo.value)
    assert str(path) in message
    assert "NAN_API_KEY" in message
    assert "export" in message


def test_env_file_that_does_not_exist_raises_naming_the_path(tmp_path: Path) -> None:
    path = tmp_path / "absent.env"

    with pytest.raises(NanConfigError) as excinfo:
        load_api_key_from_env_file(path)

    message = str(excinfo.value)
    assert str(path) in message
    assert "NAN_API_KEY" in message


def test_env_file_errors_never_echo_the_file_contents(tmp_path: Path) -> None:
    secret = "CONTENTS-MUST-NOT-LEAK-1234567890"
    path = tmp_path / "undecodable.env"
    path.write_bytes(b"\xff\xfe" + secret.encode("utf-8"))

    with pytest.raises(NanConfigError) as excinfo:
        load_api_key_from_env_file(path)

    message = str(excinfo.value)
    assert str(path) in message
    assert secret not in message


def test_default_env_file_path_follows_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    assert default_env_file_path() == home / ".xfinaudio" / "apiIA.env"


def test_chat_prefers_the_environment_variable_over_the_env_file(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.setenv("NAN_API_KEY", API_KEY)
    env_file = write_env_file(tmp_path, f"{FILE_KEY}\n")
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport, env_file=env_file)

    assert header_of(transport.request, "Authorization") == f"Bearer {API_KEY}"


def test_chat_falls_back_to_the_env_file_when_the_environment_variable_is_blank(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.setenv("NAN_API_KEY", "   ")
    env_file = write_env_file(tmp_path, f"{FILE_KEY}\n")
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport, env_file=env_file)

    assert header_of(transport.request, "Authorization") == f"Bearer {FILE_KEY}"


def test_chat_reads_the_explicit_env_file_argument(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    env_file = write_env_file(tmp_path, f"NAN_API_KEY={FILE_KEY}\n", name="explicit.env")
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport, env_file=env_file)

    assert header_of(transport.request, "Authorization") == f"Bearer {FILE_KEY}"


def test_explicit_env_file_argument_beats_the_environment_path(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "wrong.env"))
    env_file = write_env_file(tmp_path, FILE_KEY, name="explicit.env")
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport, env_file=env_file)

    assert header_of(transport.request, "Authorization") == f"Bearer {FILE_KEY}"


def test_chat_reads_the_env_file_named_by_the_environment(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    env_file = write_env_file(tmp_path, f"{FILE_KEY}\n", name="from-environment.env")
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(env_file))
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert header_of(transport.request, "Authorization") == f"Bearer {FILE_KEY}"


def test_chat_reads_the_default_home_env_file(monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    monkeypatch.delenv("XFINAUDIO_AI_ENV_FILE", raising=False)
    home = tmp_path / "home"
    (home / ".xfinaudio").mkdir(parents=True)
    write_env_file(home / ".xfinaudio", FILE_KEY + "\n")
    monkeypatch.setenv("HOME", str(home))
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert header_of(transport.request, "Authorization") == f"Bearer {FILE_KEY}"


def test_chat_key_error_names_the_env_file_path_it_tried(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    missing = tmp_path / "missing-key.env"
    transport = FakeTransport(completion_body("unused"))

    with pytest.raises(NanConfigError) as excinfo:
        chat("hi", transport=transport, env_file=missing)

    message = str(excinfo.value)
    assert str(missing) in message
    assert "NAN_API_KEY" in message
    assert transport.requests == [], "a key error must fail before any transport call"


def test_chat_key_error_names_the_default_home_path(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    monkeypatch.delenv("XFINAUDIO_AI_ENV_FILE", raising=False)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    with pytest.raises(NanConfigError) as excinfo:
        chat("hi", transport=FakeTransport(completion_body("unused")))

    assert str(home / ".xfinaudio" / "apiIA.env") in str(excinfo.value)


def test_chat_error_text_never_carries_a_key_loaded_from_the_env_file(
    monkeypatch: pytest.MonkeyPatch, ai_env: None, tmp_path: Path
) -> None:
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    env_file = write_env_file(tmp_path, f"{FILE_KEY}\n")
    transport = FakeTransport(http_unauthorized())

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", transport=transport, env_file=env_file)

    error = excinfo.value
    rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    assert FILE_KEY not in rendered


# --------------------------------------------------------------------------- S9a
# One surface -- the list chat -- asks for a JSON answer at a low temperature, and a
# provider that refuses ``response_format`` is asked once more without it.


def http_bad_request(detail: str) -> urllib.error.HTTPError:
    headers: Message[str, str] = Message()
    return urllib.error.HTTPError(
        CONFIGURED_ENDPOINT, 400, "Bad Request", headers, io.BytesIO(detail.encode("utf-8"))
    )


class SequenceTransport:
    """A fake transport that returns or raises one queued outcome per call."""

    def __init__(self, *outcomes: bytes | BaseException) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> FakeResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return FakeResponse(outcome)

    def body(self, index: int) -> dict[str, Any]:
        data = self.requests[index].data
        assert data is not None, "the request carried no body"
        decoded = json.loads(data.decode("utf-8"))
        assert isinstance(decoded, dict)
        return decoded


def test_chat_sends_only_the_model_and_the_messages_unless_a_shape_is_requested(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    chat("hi", transport=transport)

    assert set(payload_of(transport)) == {"model", "messages"}


def test_chat_asks_for_a_json_object_and_a_temperature_when_requested(ai_env: None) -> None:
    transport = FakeTransport(completion_body('{"reply": "ok", "actions": []}'))

    chat("hi", json_object=True, temperature=0.2, transport=transport)

    payload = payload_of(transport)
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0.2
    assert payload["messages"] == [{"role": "user", "content": "hi"}]


def test_a_provider_that_rejects_the_json_object_is_asked_once_more_without_it(ai_env: None) -> None:
    transport = SequenceTransport(
        http_bad_request('{"error": {"message": "response_format is not supported"}}'),
        completion_body('{"reply": "ok", "actions": []}'),
    )

    answer = chat("hi", json_object=True, temperature=0.2, transport=transport)

    assert answer == '{"reply": "ok", "actions": []}'
    assert len(transport.requests) == 2
    first, retry = transport.body(0), transport.body(1)
    assert first["response_format"] == {"type": "json_object"}
    assert "response_format" not in retry
    assert retry["temperature"] == first["temperature"] == 0.2
    assert retry["messages"] == first["messages"]


def test_a_rejection_that_does_not_name_the_json_object_is_not_retried(ai_env: None) -> None:
    transport = SequenceTransport(http_bad_request('{"error": {"message": "unknown model"}}'))

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", json_object=True, temperature=0.2, transport=transport)

    assert "400" in str(excinfo.value)
    assert len(transport.requests) == 1


def test_a_second_rejection_of_the_json_object_ends_the_call_after_one_retry(ai_env: None) -> None:
    transport = SequenceTransport(
        http_bad_request("response_format unavailable"),
        http_bad_request("response_format unavailable"),
    )

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", json_object=True, temperature=0.2, transport=transport)

    assert "400" in str(excinfo.value)
    assert len(transport.requests) == 2
    assert "response_format" not in transport.body(1)


def test_a_rejection_without_a_readable_body_is_not_retried(ai_env: None) -> None:
    headers: Message[str, str] = Message()
    transport = SequenceTransport(
        urllib.error.HTTPError(CONFIGURED_ENDPOINT, 400, "Bad Request", headers, None)
    )

    with pytest.raises(NanRequestError) as excinfo:
        chat("hi", json_object=True, transport=transport)

    assert "400" in str(excinfo.value)
    assert len(transport.requests) == 1


def test_a_temperature_that_is_not_a_bounded_number_is_refused_before_any_call(ai_env: None) -> None:
    transport = FakeTransport(completion_body("ok"))

    with pytest.raises((ValueError, NanConfigError)):
        chat("hi", temperature=9.5, transport=transport)

    assert transport.requests == []
