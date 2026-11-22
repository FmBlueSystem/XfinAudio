"""Nan Builders (OpenAI-compatible) chat client for XfinAudio.

Function-level, stdlib-only, and offline by default. Nothing here
opens a socket unless ``XFINAUDIO_AI_ENABLED`` opts in *and* an API key is
available. The key value only ever reaches the ``Authorization`` header: it is
not logged, echoed in errors, or stored anywhere else.

Keys resolve environment first (``NAN_API_KEY``), then an operator-owned env
file whose path comes from an explicit argument, ``XFINAUDIO_AI_ENV_FILE``, or
``~/.xfinaudio/apiIA.env``. Configured user-requested actions may call the provider; ``transport`` exists
so automated tests can verify the request without using the network.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_ENDPOINT = "https://api.nan.builders/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"

#: The Nan API (fronted by a CDN) rejects the default ``Python-urllib`` user
#: agent with HTTP 403. Identify the app instead; observed live 2026-09-28.
USER_AGENT = "XfinAudio/1.8 (+https://github.com/FmBlueSystem/XfinAudio)"

TRUTHY_FLAG_VALUES = frozenset({"1", "true", "yes"})

ENABLED_ENV = "XFINAUDIO_AI_ENABLED"
API_KEY_ENV = "NAN_API_KEY"
ENDPOINT_ENV = "NAN_API_BASE"
MODEL_ENV = "NAN_MODEL"
ENV_FILE_ENV = "XFINAUDIO_AI_ENV_FILE"

#: Injectable transport. ``chat`` calls it as ``transport(request, timeout=...)``,
#: so a caller can supply a fake and keep the adapter fully offline.
Transport = Callable[..., Any]

#: The JSON answer shape an OpenAI-compatible provider accepts.
JSON_OBJECT_FORMAT = {"type": "json_object"}
#: The field a provider names when it refuses that shape; the only rejection worth a retry.
RESPONSE_FORMAT_FIELD = "response_format"
#: How much of the provider's error body is read to recognise that rejection.
MAX_ERROR_BODY_BYTES = 4 * 1024
#: The temperature range an OpenAI-compatible provider accepts.
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0


@dataclass(frozen=True)
class _RequestContext:
    enabled: bool
    key_provider: Callable[[], str] = field(repr=False)
    endpoint: str
    model: str


_REQUEST_CONTEXT: ContextVar[_RequestContext | None] = ContextVar("xfinaudio_ai_request", default=None)


@contextmanager
def request_context(
    *, enabled: bool, key_provider: Callable[[], str], endpoint: str = DEFAULT_ENDPOINT, model: str = DEFAULT_MODEL
) -> Iterator[None]:
    """Bind one explicit request without inspecting or mutating process configuration."""
    if type(enabled) is not bool or not callable(key_provider):
        raise NanConfigError("Invalid explicit AI request configuration")
    token = _REQUEST_CONTEXT.set(_RequestContext(enabled, key_provider, endpoint, model))
    try:
        yield
    finally:
        _REQUEST_CONTEXT.reset(token)


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Credential-bearing API calls must target their final HTTPS endpoint."""

    def redirect_request(
        self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def _urlopen(request: urllib.request.Request, *, timeout: float) -> Any:
    if _REQUEST_CONTEXT.get() is not None:
        return urllib.request.build_opener(urllib.request.ProxyHandler({}), _RejectRedirects()).open(
            request, timeout=timeout
        )
    return urllib.request.build_opener(_RejectRedirects()).open(request, timeout=timeout)


class NanConfigError(Exception):
    """Raised when AI is requested but the adapter is not configured for it."""


class NanRequestError(Exception):
    """Raised when a Nan Builders request fails. Never carries the API key."""


def is_ai_enabled() -> bool:
    """Return True only when ``XFINAUDIO_AI_ENABLED`` explicitly opts in (default off)."""
    if context := _REQUEST_CONTEXT.get():
        return context.enabled
    return os.environ.get(ENABLED_ENV, "").strip().lower() in TRUTHY_FLAG_VALUES


def default_env_file_path() -> Path:
    """Return the operator-facing env file used when nothing overrides it.

    Resolved per call, not at import time, so a test or a launcher that moves
    ``HOME`` is honored.
    """
    return Path.home() / ".xfinaudio" / "apiIA.env"


def load_api_key_from_env_file(path: Path) -> str:
    """Return the API key stored in ``path``.

    Two shapes are accepted, because the operator-facing file may be either a
    bare key alone on one line (no ``KEY=`` prefix) or dotenv-style content with
    comments, blank lines, and ``NAN_API_KEY=<value>``. An explicit
    ``NAN_API_KEY=`` line wins over a bare line. The file contents never reach
    an error message; only the path does.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise NanConfigError(
            f"AI is enabled but the {API_KEY_ENV} env file could not be read ({type(exc).__name__}): {path}. "
            f"Create it with the bare key on one line, or set {API_KEY_ENV} in the environment, "
            f'for example: export {API_KEY_ENV}="<your-nan-builders-key>".'
        ) from None

    api_key = _parse_env_file(text)
    if not api_key:
        raise NanConfigError(
            f"AI is enabled but {path} holds no {API_KEY_ENV} value. Write the bare key on one line "
            f"(or {API_KEY_ENV}=<key>), or set {API_KEY_ENV} in the environment, "
            f'for example: export {API_KEY_ENV}="<your-nan-builders-key>".'
        )
    return api_key


#: The only roles a conversation may carry (OpenAI-compatible chat roles).
CHAT_ROLES = frozenset({"system", "user", "assistant"})


def chat(
    message: str,
    *,
    messages: Sequence[Mapping[str, str]] | None = None,
    system: str | None = None,
    model: str | None = None,
    timeout: float = 30.0,
    transport: Transport | None = None,
    env_file: Path | None = None,
    enabled: bool | None = None,
    json_object: bool = False,
    temperature: float | None = None,
) -> str:
    """Send one chat completion request and return the assistant's text.

    AI must be enabled and keyed before this is reached, so failure is always an
    exception (``NanConfigError`` for configuration, ``NanRequestError`` for the
    request itself) rather than a silent empty answer. The API key value is
    never included in the raised errors. ``enabled`` is an explicit per-call
    opt-in for a user-triggered connection probe; it never changes runtime state.

    ``messages`` carries a whole conversation as ``{"role", "content"}``
    mappings with roles ``system``, ``user`` or ``assistant``. When given, the
    request body carries exactly those messages in that order and ``message``
    and ``system`` are unused; when omitted, the body is built from ``message``
    and ``system`` exactly as before. An invalid conversation raises
    ``ValueError`` before any network call.

    ``json_object`` and ``temperature`` shape the answer, and only the caller that
    needs them sets them: the list chat asks for one JSON object at a low
    temperature. A provider that refuses ``response_format`` with HTTP 400 naming
    the field is asked once more without it, so one rejected request still ends
    with an answer instead of a failed turn. Every attempt is one bounded call.
    """
    conversation = _validated_messages(messages) if messages is not None else None
    _validated_temperature(temperature)

    if not (is_ai_enabled() if enabled is None or _REQUEST_CONTEXT.get() is not None else enabled):
        raise NanConfigError(
            f"AI is disabled: set {ENABLED_ENV}=1 in the environment before starting XfinAudio "
            "to allow Nan Builders requests."
        )

    api_key = _resolve_api_key(env_file)
    request = _build_request(
        message,
        messages=conversation,
        system=system,
        model=model,
        api_key=api_key,
        json_object=json_object,
        temperature=temperature,
    )
    retry = (
        _request_builder(
            message,
            messages=conversation,
            system=system,
            model=model,
            api_key=api_key,
            temperature=temperature,
        )
        if json_object
        else None
    )
    send = transport or _urlopen
    return _parse_content(_send(send, request, timeout, retry))


def _request_builder(
    message: str,
    *,
    messages: Sequence[dict[str, str]] | None,
    system: str | None,
    model: str | None,
    api_key: str,
    temperature: float | None,
) -> Callable[[], urllib.request.Request]:
    """The same request without ``response_format``, built only if it is needed."""

    def build() -> urllib.request.Request:
        return _build_request(
            message,
            messages=messages,
            system=system,
            model=model,
            api_key=api_key,
            temperature=temperature,
        )

    return build


def _send(
    send: Transport, request: urllib.request.Request, timeout: float, retry: Callable[[], urllib.request.Request] | None
) -> bytes:
    """One request's body, retried at most once without the answer shape this provider refuses."""
    try:
        with send(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if retry is not None and _rejects_json_object(exc):
            return _send(send, retry(), timeout, None)
        raise NanRequestError(f"Nan Builders request failed with HTTP status {exc.code}.") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise NanRequestError(_timeout_message(timeout)) from None
        raise NanRequestError("Nan Builders request failed: Connection refused or network unavailable.") from None
    except TimeoutError:
        raise NanRequestError(_timeout_message(timeout)) from None
    except OSError:
        raise NanRequestError("Nan Builders request failed: network unavailable.") from None
    except ValueError:
        raise NanConfigError("Invalid API credential or request configuration.") from None


def _rejects_json_object(error: urllib.error.HTTPError) -> bool:
    """Whether a 400 answer names ``response_format``: the one rejection a retry can fix."""
    if error.code != 400:
        return False
    try:
        body = error.read(MAX_ERROR_BODY_BYTES)
    except Exception:
        # A body the error object cannot expose is not evidence of this rejection.
        return False
    if not isinstance(body, bytes):
        return False
    return RESPONSE_FORMAT_FIELD in body.decode("utf-8", errors="ignore")


def _validated_temperature(temperature: float | None) -> None:
    """Accept only a bounded number, and never a whole number spelled as one."""
    if temperature is None:
        return
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ValueError("temperature must be a number between 0 and 2.")
    if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
        raise ValueError("temperature must be a number between 0 and 2.")


def _resolve_api_key(env_file: Path | None = None) -> str:
    """Return the API key: environment variable first, then the operator env file."""
    if context := _REQUEST_CONTEXT.get():
        return context.key_provider()
    env_key = os.environ.get(API_KEY_ENV)
    if env_key and env_key.strip():
        return env_key.strip()
    return load_api_key_from_env_file(_resolve_env_file_path(env_file))


def _resolve_env_file_path(env_file: Path | None = None) -> Path:
    """Return the env file path: explicit argument, then env override, then the default."""
    if env_file is not None:
        return env_file
    override = os.environ.get(ENV_FILE_ENV)
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return default_env_file_path()


def _validated_messages(messages: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Return a copy of ``messages``, rejecting anything the provider would refuse.

    Called before the request is built so an invalid conversation can never
    reach the transport, the credential file, or the network.
    """
    if isinstance(messages, (str, bytes)):
        raise ValueError("messages must be a sequence of {'role', 'content'} messages, not a string.")
    try:
        entries = list(messages)
    except TypeError:
        raise ValueError("messages must be a sequence of {'role', 'content'} messages.") from None
    if not entries:
        raise ValueError("messages must contain at least one message.")

    validated: list[dict[str, str]] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, Mapping):
            raise ValueError(f"message {index} must be a mapping with 'role' and 'content'.")
        if set(entry) != {"role", "content"}:
            raise ValueError(f"message {index} must have exactly the keys 'role' and 'content'.")
        role = entry["role"]
        content = entry["content"]
        if not isinstance(role, str) or role not in CHAT_ROLES:
            raise ValueError(f"message {index} has an invalid role; use one of {sorted(CHAT_ROLES)}.")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"message {index} has empty content.")
        validated.append({"role": role, "content": content})
    return validated


def _build_request(
    message: str,
    *,
    messages: Sequence[dict[str, str]] | None,
    system: str | None,
    model: str | None,
    api_key: str,
    json_object: bool = False,
    temperature: float | None = None,
) -> urllib.request.Request:
    request_messages: list[dict[str, str]] = []
    if messages is not None:
        request_messages.extend(messages)
    else:
        if system is not None:
            request_messages.append({"role": "system", "content": system})
        request_messages.append({"role": "user", "content": message})

    body = json.dumps(_body_fields(model, request_messages, json_object, temperature)).encode("utf-8")
    request = urllib.request.Request(_resolve_endpoint(), data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("User-Agent", USER_AGENT)
    request.add_unredirected_header("Authorization", f"Bearer {api_key}")
    return request


def _body_fields(
    model: str | None, messages: Sequence[dict[str, str]], json_object: bool, temperature: float | None
) -> dict[str, Any]:
    """The provider body: the model and the conversation, plus the answer shape when asked."""
    fields: dict[str, Any] = {"model": _resolve_model(model), "messages": list(messages)}
    if temperature is not None:
        fields["temperature"] = temperature
    if json_object:
        fields["response_format"] = dict(JSON_OBJECT_FORMAT)
    return fields


def _resolve_endpoint() -> str:
    context = _REQUEST_CONTEXT.get()
    endpoint = context.endpoint if context is not None else os.environ.get(ENDPOINT_ENV) or DEFAULT_ENDPOINT
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        valid = (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment
            and (parsed.port is None or 0 < parsed.port <= 65535)
            and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in endpoint)
        )
    except ValueError:
        valid = False
    if not valid:
        raise NanConfigError(f"{ENDPOINT_ENV} must be an absolute HTTPS URL without credentials or fragments.")
    return endpoint


def _resolve_model(model: str | None) -> str:
    if context := _REQUEST_CONTEXT.get():
        return context.model
    return model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL


def _parse_env_file(text: str) -> str:
    """Extract the key from bare or dotenv-style file content."""
    bare: str | None = None
    named: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            if bare is None:
                bare = _unquote(line)
            continue
        name, _, value = line.partition("=")
        if name.strip() == API_KEY_ENV and named is None:
            named = _unquote(value)
    return named or bare or ""


def _unquote(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1].strip()
    return stripped


def _parse_content(raw_body: bytes) -> str:
    """Extract ``choices[0].message.content`` from an OpenAI-style body."""
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise NanRequestError("Nan Builders returned a body that is not valid JSON.") from None

    content: object = None
    if isinstance(payload, dict):
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                response_message = first.get("message")
                if isinstance(response_message, dict):
                    content = response_message.get("content")

    if not isinstance(content, str):
        raise NanRequestError("Nan Builders response is missing choices[0].message.content.")
    return content


def _timeout_message(timeout: float) -> str:
    return f"Nan Builders request timed out after {timeout:g}s."
