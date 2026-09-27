"""Nan Builders (OpenAI-compatible) chat client for XfinAudio.

Fase 0 spike: function-level, stdlib-only, and offline by default. Nothing here
opens a socket unless ``XFINAUDIO_AI_ENABLED`` opts in *and* an API key is
available. The key value only ever reaches the ``Authorization`` header: it is
not logged, echoed in errors, or stored anywhere else.

Keys resolve environment first (``NAN_API_KEY``), then an operator-owned env
file whose path comes from an explicit argument, ``XFINAUDIO_AI_ENV_FILE``, or
``~/.xfinaudio/apiIA.env``. Live calls are intentionally out of scope for this
spike; ``transport`` exists so tests can pin the request without the network.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
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

_urlopen: Transport = urllib.request.urlopen


class NanConfigError(Exception):
    """Raised when AI is requested but the adapter is not configured for it."""


class NanRequestError(Exception):
    """Raised when a Nan Builders request fails. Never carries the API key."""


def is_ai_enabled() -> bool:
    """Return True only when ``XFINAUDIO_AI_ENABLED`` explicitly opts in (default off)."""
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


def chat(
    message: str,
    *,
    system: str | None = None,
    model: str | None = None,
    timeout: float = 30.0,
    transport: Transport | None = None,
    env_file: Path | None = None,
) -> str:
    """Send one chat completion request and return the assistant's text.

    AI must be enabled and keyed before this is reached, so failure is always an
    exception (``NanConfigError`` for configuration, ``NanRequestError`` for the
    request itself) rather than a silent empty answer. The API key value is
    never included in the raised errors.
    """
    if not is_ai_enabled():
        raise NanConfigError(
            f"AI is disabled: set {ENABLED_ENV}=1 in the environment before starting XfinAudio "
            "to allow Nan Builders requests."
        )

    api_key = _resolve_api_key(env_file)
    request = _build_request(message, system=system, model=model, api_key=api_key)
    send = transport or _urlopen
    try:
        with send(request, timeout=timeout) as response:
            raw_body = response.read()
    except urllib.error.HTTPError as exc:
        raise NanRequestError(f"Nan Builders request failed with HTTP status {exc.code}.") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise NanRequestError(_timeout_message(timeout)) from None
        raise NanRequestError(f"Nan Builders request failed: {exc.reason}.") from None
    except TimeoutError:
        raise NanRequestError(_timeout_message(timeout)) from None
    except OSError as exc:
        raise NanRequestError(f"Nan Builders request failed: {exc}.") from None

    return _parse_content(raw_body)


def _resolve_api_key(env_file: Path | None = None) -> str:
    """Return the API key: environment variable first, then the operator env file."""
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


def _build_request(message: str, *, system: str | None, model: str | None, api_key: str) -> urllib.request.Request:
    messages: list[dict[str, str]] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    body = json.dumps({"model": _resolve_model(model), "messages": messages}).encode("utf-8")
    request = urllib.request.Request(_resolve_endpoint(), data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Authorization", f"Bearer {api_key}")
    return request


def _resolve_endpoint() -> str:
    return os.environ.get(ENDPOINT_ENV) or DEFAULT_ENDPOINT


def _resolve_model(model: str | None) -> str:
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
