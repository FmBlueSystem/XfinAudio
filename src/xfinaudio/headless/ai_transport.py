"""Confirmed, bounded provider requests with explicit credential-source identity."""

from __future__ import annotations

import math
import os
import stat
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


def _read_key(binding: CredentialBinding) -> str:
    try:
        _current(binding)
        with open_directory(binding.path.parent) as (parent, lineage):
            descriptor = os.open(binding.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                info = os.fstat(descriptor)
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


def _bounded_transport(transport: Transport | None, maximum_timeout: int) -> Transport:
    @contextmanager
    def send(request: urllib.request.Request, *, timeout: float) -> Iterator[_BoundedResponse]:
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
        with (transport or nan_client._urlopen)(request, timeout=timeout) as response:
            yield _BoundedResponse(response)

    return send


def provider_request(
    settings: AiSettings,
    binding: CredentialBinding | None,
    callback: Callable[[Transport], _Result],
    transport: Transport | None = None,
    *,
    surface: str = "library",
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
            return callback(_bounded_transport(transport, AI_REQUEST_TIMEOUT_SECONDS[surface]))
    except BackendError:
        raise
    except Exception:
        raise BackendError("ai_request_failed", "The provider request failed; no response was applied") from None
