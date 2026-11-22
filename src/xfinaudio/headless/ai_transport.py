"""Confirmed, bounded provider requests with explicit credential-source identity."""

from __future__ import annotations

import contextvars
import math
import os
import stat
import threading
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from xfinaudio.ai import nan_client
from xfinaudio.ai.nan_client import DEFAULT_ENDPOINT, DEFAULT_MODEL, Transport, request_context
from xfinaudio.config.settings import AiSettings
from xfinaudio.headless.ai_protocol import AI_REQUEST_TIMEOUT_SECONDS
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_safety import open_directory, source_identity

MAX_CREDENTIAL_BYTES = MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
#: The code a call reaches the app with when its own budget expired (S2).
AI_TIMEOUT_CODE = "ai_timeout"

#: Group or other permission bits. A credential file that grants any of them is
#: readable (or writable) by another local account, so it is refused unread.
GROUP_OTHER_ACCESS = 0o077
PERMISSION_ERROR_CODE = "ai_credential_permissions"
_PERMISSION_MESSAGE = (
    "The selected credential file is readable by other users; "
    "restrict it to your account with chmod 600 on that file and request again"
)
_Result = TypeVar("_Result")


@dataclass(frozen=True)
class CredentialBinding:
    """Private native-selected file metadata, never file contents or a public DTO."""

    path: Path = field(repr=False)
    identity: tuple[object, ...]


def bind_credential(path: Path) -> CredentialBinding:
    """Bind regular file/parent identities without reading a credential byte."""
    try:
        if not isinstance(path, Path) or not path.is_absolute() or len(str(path)) > 4096 or "\x00" in str(path):
            raise ValueError
        identity = source_identity(path)
        if _file_size(identity) > MAX_CREDENTIAL_BYTES:
            raise ValueError
        return CredentialBinding(path, identity)
    except (OSError, ValueError):
        raise BackendError(
            "ai_credentials_unavailable", "The selected credential file is unavailable or unsafe"
        ) from None


def _file_size(identity: tuple[object, ...]) -> int:
    size = identity[3]
    if not isinstance(size, int):
        raise ValueError
    return size


def _current(binding: CredentialBinding) -> None:
    try:
        if source_identity(binding.path) != binding.identity:
            raise ValueError
    except (OSError, ValueError):
        raise BackendError(
            "stale_credential", "The selected credential file changed; review the request again"
        ) from None


def _descriptor_identity(info: os.stat_result, lineage: object) -> tuple[object, ...]:
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CREDENTIAL_BYTES:
        raise ValueError
    return lineage, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _reject_group_other_access(mode: int) -> None:
    """Refuse a descriptor other accounts may open; never echoes the path or contents."""
    if mode & GROUP_OTHER_ACCESS:
        raise BackendError(PERMISSION_ERROR_CODE, _PERMISSION_MESSAGE)


def _read_key(binding: CredentialBinding) -> str:
    try:
        _current(binding)
        with open_directory(binding.path.parent) as (parent, lineage):
            descriptor = os.open(binding.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                info = os.fstat(descriptor)
                _reject_group_other_access(info.st_mode)
                if _descriptor_identity(info, lineage) != binding.identity:
                    raise ValueError
                data = bytearray()
                while len(data) < info.st_size:
                    chunk = os.read(descriptor, info.st_size - len(data))
                    if not chunk:
                        break
                    data.extend(chunk)
                if _descriptor_identity(os.fstat(descriptor), lineage) != binding.identity or len(data) != info.st_size:
                    raise ValueError
                _current(binding)
            finally:
                os.close(descriptor)
        key = nan_client._parse_env_file(data.decode("utf-8"))
        if not key or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in key):
            raise ValueError
        return key
    except (OSError, ValueError):
        raise BackendError(
            "ai_credentials_unavailable", "The selected credential file could not be used safely"
        ) from None


def _timeout_message(timeout: float) -> str:
    return f"The provider did not answer within the {timeout:g}s this call is allowed; the turn ended without applying anything"


class _BoundedResponse:
    def __init__(self, response: Any) -> None:
        self._response = response
        self._remaining = MAX_RESPONSE_BYTES

    def read(self, size: int = -1) -> bytes:
        limit = self._remaining + 1 if size < 0 else min(size, self._remaining + 1)
        data = self._response.read(limit)
        if not isinstance(data, bytes) or len(data) > self._remaining:
            raise BackendError("ai_request_failed", "The provider response exceeds the supported limit")
        self._remaining -= len(data)
        return data


class _BufferedResponse:
    """The bounded body of one call, served after the call's own deadline was enforced."""

    def __init__(self, body: bytes) -> None:
        self._body = body
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        end = len(self._body) if size < 0 else min(len(self._body), self._offset + size)
        data = self._body[self._offset : end]
        self._offset = end
        return data


#: A drain listener receives the way to close the call in flight and returns how to retire it.
Drain = Callable[[Callable[[], None]], Callable[[], None]]


def _bounded_transport(
    transport: Transport | None, maximum_timeout: int, register: Drain | None = None
) -> Transport:
    """Wrap one provider call with the app's own bound (S2).

    The transport is entered and its body read in a worker thread so the deadline belongs to
    this app: a transport that ignores the ``timeout`` it is given (a hung socket, a provider that
    drips bytes) is cut at the budget instead of holding the turn forever. The thread is a daemon
    and the response is closed by the cancellation drain, so neither outlives the turn.
    """

    @contextmanager
    def send(request: urllib.request.Request, *, timeout: float) -> Iterator[_BufferedResponse]:
        if (
            not isinstance(request, urllib.request.Request)
            or request.full_url != DEFAULT_ENDPOINT
            or request.get_method() != "POST"
            or not isinstance(request.data, bytes)
            or len(request.data) > MAX_REQUEST_BYTES
            or type(timeout) not in (int, float)
            or not 0 < timeout <= maximum_timeout
            or not math.isfinite(timeout)
        ):
            raise BackendError("ai_request_failed", "The provider request exceeds the permitted scope")
        outcome: list[object] = []
        in_flight: list[Any] = []

        def close() -> None:
            response = in_flight[0] if in_flight else None
            if response is not None:
                response.close()

        def call() -> None:
            try:
                with (transport or nan_client._urlopen)(request, timeout=timeout) as response:
                    in_flight.append(response)
                    outcome.append(_BoundedResponse(response).read())
            except BaseException as failure:  # re-raised in the caller's thread, never lost
                outcome.append(failure)

        retire = register(close) if register is not None else (lambda: None)
        try:
            # The request context is a ContextVar, and a plain thread starts without it: the
            # worker must run inside a copy, or the pinned endpoint and credential provider
            # would be missing from the very call they authorize.
            worker = threading.Thread(
                target=contextvars.copy_context().run, args=(call,), name="xfinaudio-provider-call", daemon=True
            )
            worker.start()
            worker.join(timeout)
            if worker.is_alive():
                raise BackendError(AI_TIMEOUT_CODE, _timeout_message(timeout))
        finally:
            retire()
        if not outcome:
            raise BackendError("ai_request_failed", "The provider request ended without a response")
        result = outcome[0]
        if isinstance(result, TimeoutError):
            raise BackendError(AI_TIMEOUT_CODE, _timeout_message(timeout))
        if isinstance(result, BaseException):
            raise result
        if not isinstance(result, bytes):
            raise BackendError("ai_request_failed", "The provider response could not be read")
        yield _BufferedResponse(result)

    return send


def provider_request(
    settings: AiSettings,
    binding: CredentialBinding | None,
    callback: Callable[[Transport], _Result],
    transport: Transport | None = None,
    *,
    surface: str = "library",
    register_drain: Drain | None = None,
) -> _Result:
    """Run one confirmed callback using only its explicit settings and fixed recipient."""
    if not isinstance(surface, str) or surface not in AI_REQUEST_TIMEOUT_SECONDS:
        raise BackendError("ai_request_failed", "The provider request has no permitted timeout policy")
    if not settings.enabled:
        raise BackendError("ai_disabled", "Enable optional AI before making a request")
    if settings.env_file is None or binding is None:
        raise BackendError("ai_unconfigured", "Select a credential file before making a request")
    if not isinstance(binding, CredentialBinding) or settings.env_file != binding.path:
        raise BackendError("stale_credential", "The selected credential file changed; review the request again")
    _current(binding)
    try:
        with request_context(
            enabled=True, key_provider=lambda: _read_key(binding), endpoint=DEFAULT_ENDPOINT, model=DEFAULT_MODEL
        ):
            return callback(_bounded_transport(transport, AI_REQUEST_TIMEOUT_SECONDS[surface], register_drain))
    except BackendError:
        raise
    except Exception:
        raise BackendError("ai_request_failed", "The provider request failed; no response was applied") from None
