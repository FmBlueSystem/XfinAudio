"""S11: a credential file readable by group or other is rejected before any byte is read."""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

from xfinaudio.ai import nan_client as client
from xfinaudio.config.settings import AiSettings
from xfinaudio.headless.ai_transport import bind_credential, provider_request
from xfinaudio.headless.common import BackendError

SECRET = "synthetic-permission-fixture-token"
PERMISSION_CODE = "ai_credential_permissions"
CONTENTS = f"NAN_API_KEY={SECRET}\n".encode()


@pytest.fixture(autouse=True)
def no_real_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real provider calls are forbidden")

    monkeypatch.setattr(client, "_urlopen", forbidden)


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[object] = []
        self.timeouts: list[float] = []

    def __call__(self, request, *, timeout):
        self.requests.append(request)
        self.timeouts.append(timeout)
        return io.BytesIO(b'{"choices":[{"message":{"content":"synthetic response"}}]}')


def credential_file(directory: Path, mode: int, content: bytes = CONTENTS) -> Path:
    path = directory.resolve() / "selected.env"
    path.write_bytes(content)
    path.chmod(mode)
    return path


def send(path: Path, transport: FakeTransport) -> str:
    return provider_request(
        AiSettings(enabled=True, env_file=path),
        bind_credential(path),
        lambda send: client.chat("Synthetic prompt", transport=send),
        transport=transport,
    )


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o660, 0o777])
def test_group_or_other_access_is_rejected_before_the_secret_is_read(tmp_path, monkeypatch, mode):
    path = credential_file(tmp_path, mode)
    transport = FakeTransport()
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("A rejected credential must never be read"))

    with pytest.raises(BackendError) as failure:
        send(path, transport)

    assert failure.value.code == PERMISSION_CODE
    message = str(failure.value)
    assert "chmod 600" in message
    assert SECRET not in message and str(path) not in message
    assert transport.requests == []
    assert path.read_bytes() == CONTENTS, "the rejected file must be left untouched"


def test_rejection_precedes_parsing_so_an_unusable_body_still_reports_permissions(tmp_path):
    path = credential_file(tmp_path, 0o644, b"not a credential\n")
    transport = FakeTransport()

    with pytest.raises(BackendError) as failure:
        send(path, transport)

    assert failure.value.code == PERMISSION_CODE and transport.requests == []


@pytest.mark.parametrize("mode", [0o600, 0o400])
def test_owner_only_modes_are_accepted_exactly_as_before(tmp_path, mode):
    path = credential_file(tmp_path, mode)
    transport = FakeTransport()

    assert send(path, transport) == "synthetic response"
    assert len(transport.requests) == 1
    assert transport.requests[0].get_header("Authorization") == f"Bearer {SECRET}"
    assert transport.timeouts == [30.0]


def test_owner_only_credential_still_completes_a_confirmed_request_end_to_end(tmp_path):
    path = credential_file(tmp_path, 0o600)

    assert send(path, FakeTransport()) == "synthetic response"
    assert path.read_bytes() == CONTENTS


@pytest.mark.parametrize("state", ["missing", "directory", "oversized"])
def test_existing_unavailable_rejections_keep_their_code(tmp_path, state):
    root = tmp_path.resolve()
    path = root / "selected.env"
    if state == "directory":
        path.mkdir()
    elif state == "oversized":
        path.write_bytes(b"x" * (64 * 1024 + 1))
        path.chmod(0o600)

    with pytest.raises(BackendError) as failure:
        bind_credential(path)

    assert failure.value.code == "ai_credentials_unavailable"
    assert failure.value.code != PERMISSION_CODE


def test_credential_opened_by_others_after_selection_is_rejected_before_transmission(tmp_path):
    path = credential_file(tmp_path, 0o600)
    binding = bind_credential(path)
    path.chmod(0o640)
    transport = FakeTransport()

    with pytest.raises(BackendError) as failure:
        provider_request(
            AiSettings(enabled=True, env_file=path),
            binding,
            lambda send: client.chat("Synthetic prompt", transport=send),
            transport=transport,
        )

    assert failure.value.code in {PERMISSION_CODE, "stale_credential"}
    assert transport.requests == []
