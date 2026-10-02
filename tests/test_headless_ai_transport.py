"""Confirmed request context and bounded credential/transport use only dummy fixtures."""

from __future__ import annotations

import io
import json
import os
import ssl
import threading
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path

import pytest

from xfinaudio.ai import nan_client as client
from xfinaudio.config.settings import AiSettings
from xfinaudio.headless.common import BackendError

_ORIGINAL_SEND = client._urlopen


@pytest.fixture(autouse=True)
def no_real_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real provider calls are forbidden")

    monkeypatch.setattr(client, "_urlopen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)


def credential(tmp_path: Path, content: bytes = b"NAN_API_KEY=synthetic-fixture-token\n"):
    from xfinaudio.headless.ai_transport import bind_credential

    path = tmp_path.resolve() / "selected.env"
    path.write_bytes(content)
    return path, bind_credential(path)


class FakeTransport:
    def __init__(self, body: bytes | None = None):
        self.body = body if body is not None else b'{"choices":[{"message":{"content":"synthetic response"}}]}'
        self.requests = []
        self.responses = []
        self.timeouts = []

    def __call__(self, request, *, timeout):
        self.requests.append(request)
        self.timeouts.append(timeout)
        response = io.BytesIO(self.body)
        self.responses.append(response)
        return response


def ask(path, binding, transport, **kwargs):
    from xfinaudio.headless.ai_transport import provider_request

    return provider_request(
        AiSettings(enabled=True, env_file=path),
        binding,
        lambda send: client.chat("Synthetic prompt", transport=send, **kwargs),
        transport=transport,
    )


def test_context_is_explicit_and_controls_imported_references_without_environment(monkeypatch):
    from xfinaudio.ai.intent_copilot import is_ai_enabled as imported_enabled

    class NoEnvironment:
        def get(self, *args, **kwargs):
            raise AssertionError("Process environment was inspected")

    def forbidden(*args, **kwargs):
        raise AssertionError("Credential discovery was reached")

    with monkeypatch.context() as guard:
        guard.setattr(client.os, "environ", NoEnvironment())
        guard.setattr(client, "default_env_file_path", forbidden)
        guard.setattr(client, "load_api_key_from_env_file", forbidden)
        with client.request_context(enabled=True, key_provider=lambda: "synthetic-context"):
            assert imported_enabled() is True
            assert client._resolve_api_key(Path("/ignored.env")) == "synthetic-context"
            assert client._resolve_endpoint() == client.DEFAULT_ENDPOINT
            assert client._resolve_model("ignored-override") == client.DEFAULT_MODEL


def test_context_disabled_cannot_be_bypassed_and_cleanup_restores_controlled_legacy(monkeypatch):
    monkeypatch.setattr(client.os, "environ", {client.ENABLED_ENV: "1", client.API_KEY_ENV: "synthetic-legacy"})
    with (
        pytest.raises(RuntimeError),
        client.request_context(enabled=False, key_provider=lambda: pytest.fail("disabled read")),
    ):
        assert not client.is_ai_enabled()
        with pytest.raises(client.NanConfigError):
            client.chat("no", enabled=True)
        raise RuntimeError("synthetic callback failure")
    assert client.is_ai_enabled() and client._resolve_api_key() == "synthetic-legacy"


def test_context_is_nested_and_thread_isolated(monkeypatch):
    monkeypatch.setattr(client.os, "environ", {client.ENABLED_ENV: "0"})
    barrier = threading.Barrier(2)
    results = []

    def run(label):
        with client.request_context(enabled=True, key_provider=lambda: label):
            barrier.wait(3)
            results.append(client._resolve_api_key())
            with client.request_context(enabled=False, key_provider=lambda: "nested"):
                assert not client.is_ai_enabled()
            assert client._resolve_api_key() == label
        assert not client.is_ai_enabled()

    threads = [threading.Thread(target=run, args=(f"synthetic-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(4)
    assert sorted(results) == ["synthetic-0", "synthetic-1"] and not client.is_ai_enabled()


def test_binding_is_metadata_only_and_confirmed_request_uses_fixed_target(tmp_path, monkeypatch):
    from xfinaudio.headless.ai_transport import bind_credential

    path = tmp_path.resolve() / "selected.env"
    path.write_bytes(b"NAN_API_KEY='synthetic-selected'\nNAN_API_BASE=https://untrusted.invalid/\n")

    def forbidden(*args, **kwargs):
        raise AssertionError("Binding must not read contents")

    with monkeypatch.context() as block:
        block.setattr(os, "read", forbidden)
        block.setattr(Path, "read_text", forbidden)
        block.setattr(Path, "read_bytes", forbidden)
        binding = bind_credential(path)
    fake = FakeTransport()
    assert ask(path, binding, fake, model="ignored-model") == "synthetic response"
    request = fake.requests[0]
    assert request.full_url == client.DEFAULT_ENDPOINT
    assert json.loads(request.data)["model"] == client.DEFAULT_MODEL
    assert request.get_header("Authorization") == "Bearer synthetic-selected"
    assert fake.timeouts == [30.0] and fake.responses[0].closed


@pytest.mark.parametrize("state", ["disabled", "unconfigured", "wrong_path", "missing_binding"])
def test_request_checks_settings_before_read_or_network(tmp_path, state, monkeypatch):
    from xfinaudio.headless.ai_transport import provider_request

    path, binding = credential(tmp_path)
    settings = AiSettings(enabled=state != "disabled", env_file=None if state == "unconfigured" else path)
    if state == "wrong_path":
        settings = settings.model_copy(update={"env_file": tmp_path / "other.env"})
    if state == "missing_binding":
        binding = None
    fake = FakeTransport()
    monkeypatch.setattr(os, "read", lambda *a: pytest.fail("No key read before enabled/configured validation"))
    with pytest.raises(BackendError) as failure:
        provider_request(settings, binding, lambda send: client.chat("x", transport=send), transport=fake)
    assert failure.value.code in {"ai_disabled", "ai_unconfigured", "stale_credential"}
    assert not fake.requests


@pytest.mark.parametrize("kind", ["leaf_symlink", "directory_symlink", "directory", "oversized", "relative"])
def test_binding_rejects_unsafe_paths_without_content_reads(tmp_path, kind, monkeypatch):
    from xfinaudio.headless.ai_transport import bind_credential

    root = tmp_path.resolve()
    path = root / "selected.env"
    if kind == "leaf_symlink":
        target = root / "dummy.env"
        target.write_bytes(b"dummy")
        path.symlink_to(target)
    elif kind == "directory_symlink":
        child = root / "real"
        child.mkdir()
        (child / "selected.env").write_bytes(b"dummy")
        (root / "alias").symlink_to(child, target_is_directory=True)
        path = root / "alias" / "selected.env"
    elif kind == "directory":
        path.mkdir()
    elif kind == "oversized":
        path.write_bytes(b"x" * (64 * 1024 + 1))
    else:
        path = Path("relative.env")
    monkeypatch.setattr(os, "read", lambda *a: pytest.fail("Binding must not read credentials"))
    with pytest.raises(BackendError) as failure:
        bind_credential(path)
    assert failure.value.code == "ai_credentials_unavailable"
    assert str(path) not in str(failure.value)


@pytest.mark.parametrize("change", ["rewrite", "replace", "symlink", "lineage"])
def test_changed_credential_binding_fails_before_transmission(tmp_path, change):
    from xfinaudio.headless.ai_transport import bind_credential

    root = tmp_path.resolve() / "parent"
    root.mkdir()
    path, binding = credential(root)
    if change == "rewrite":
        path.write_bytes(b"synthetic-changed")
    elif change == "replace":
        alternate = root / "replacement"
        alternate.write_bytes(path.read_bytes())
        alternate.replace(path)
    elif change == "symlink":
        target = root / "other.env"
        target.write_bytes(b"synthetic-other")
        path.unlink()
        path.symlink_to(target)
    else:
        root.rename(tmp_path / "old-parent")
        root.mkdir()
        path.write_bytes(b"synthetic-new-parent")
        assert bind_credential(path) != binding
    fake = FakeTransport()
    with pytest.raises(BackendError):
        ask(path, binding, fake)
    assert not fake.requests


def test_credential_rechecked_after_bounded_read(tmp_path, monkeypatch):
    path, binding = credential(tmp_path)
    original = os.read
    sizes = []

    def mutate_after_read(descriptor, size):
        sizes.append(size)
        data = original(descriptor, size)
        path.write_bytes(b"synthetic-changed-after-read")
        return data

    monkeypatch.setattr(os, "read", mutate_after_read)
    fake = FakeTransport()
    with pytest.raises(BackendError):
        ask(path, binding, fake)
    assert max(sizes) <= 64 * 1024 and not fake.requests


@pytest.mark.parametrize("contents", [b"", b"# no key\n", b"\xff\xfe", b"NAN_API_KEY=invalid key with spaces\n"])
def test_invalid_credential_never_echoes_contents_or_path(tmp_path, contents):
    path, binding = credential(tmp_path, contents)
    with pytest.raises(BackendError) as failure:
        ask(path, binding, FakeTransport())
    assert failure.value.code == "ai_credentials_unavailable"
    assert str(path) not in str(failure.value) and "invalid key" not in str(failure.value)


@pytest.mark.parametrize("case", ["request_size", "response_size", "recipient", "timeout", "raw_failure"])
def test_transport_bounds_and_errors_are_safe_and_responses_closed(tmp_path, case):
    from xfinaudio.headless.ai_transport import provider_request

    path, binding = credential(tmp_path)
    fake = FakeTransport(b"x" * (1024 * 1024 + 1) if case == "response_size" else None)

    def callback(send):
        if case == "recipient":
            return send(urllib.request.Request("https://untrusted.invalid/", data=b"{}"), timeout=30).__enter__()
        if case == "raw_failure":
            raise RuntimeError(f"synthetic-fixture-token private path {path} RAW_PROVIDER_RESPONSE")
        return client.chat(
            "x" * (64 * 1024) if case == "request_size" else "x",
            transport=send,
            timeout=31 if case == "timeout" else 30,
        )

    with pytest.raises(BackendError) as failure:
        provider_request(AiSettings(enabled=True, env_file=path), binding, callback, transport=fake)
    assert failure.value.code == "ai_request_failed"
    assert not any(
        value in str(failure.value) for value in (str(path), "synthetic-fixture-token", "RAW_PROVIDER_RESPONSE")
    )
    assert all(response.closed for response in fake.responses)
    if case != "response_size":
        assert not fake.requests


def test_original_structured_assist_uses_context_and_fake_bounded_transport(tmp_path, monkeypatch):
    from xfinaudio.ai.structured_assists import interpret_library_query
    from xfinaudio.headless.ai_transport import provider_request

    path, binding = credential(tmp_path)
    body = json.dumps({"choices": [{"message": {"content": '{"genre":"House","bpm_min":120}'}}]}).encode()
    fake = FakeTransport(body)
    monkeypatch.setattr(client.os, "environ", {})
    query = provider_request(
        AiSettings(enabled=True, env_file=path),
        binding,
        lambda send: interpret_library_query("synthetic house query", ["House"], transport=send),
        transport=fake,
    )
    assert query.genre == "House" and query.bpm_min == 120
    assert len(fake.requests) == 1
    assert not client.is_ai_enabled()


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf"), 10**400, "30"])
def test_invalid_timeouts_never_reach_transport(tmp_path, timeout):
    path, binding = credential(tmp_path)
    fake = FakeTransport()
    with pytest.raises(BackendError) as error:
        ask(path, binding, fake, timeout=timeout)
    assert error.value.code == "ai_request_failed" and not fake.requests


@pytest.mark.parametrize("surface,limit", [("library", 30), ("prep", 60), ("review", 120), ("connection", 10)])
def test_trusted_surface_timeout_is_bounded_and_preserves_original_policy(tmp_path, surface, limit):
    from xfinaudio.headless.ai_transport import provider_request

    path, binding = credential(tmp_path)
    fake = FakeTransport()
    settings = AiSettings(enabled=True, env_file=path)
    assert (
        provider_request(
            settings,
            binding,
            lambda send: client.chat("Synthetic", transport=send, timeout=limit),
            transport=fake,
            surface=surface,
        )
        == "synthetic response"
    )
    assert fake.timeouts == [limit]
    with pytest.raises(BackendError) as error:
        provider_request(
            settings,
            binding,
            lambda send: client.chat("Synthetic", transport=send, timeout=limit + 1),
            transport=fake,
            surface=surface,
        )
    assert error.value.code == "ai_request_failed" and len(fake.requests) == 1


@pytest.mark.parametrize("surface", ["unknown", "", None, [], 120])
def test_unrecognized_timeout_policy_never_reads_credentials_or_sends(tmp_path, monkeypatch, surface):
    from xfinaudio.headless.ai_transport import provider_request

    path, binding = credential(tmp_path)
    fake = FakeTransport()
    monkeypatch.setattr(os, "read", lambda *args: pytest.fail("Invalid policy read credentials"))
    with pytest.raises(BackendError) as error:
        provider_request(
            AiSettings(enabled=True, env_file=path),
            binding,
            lambda send: client.chat("x", transport=send),
            transport=fake,
            surface=surface,
        )
    assert error.value.code == "ai_request_failed" and not fake.requests


@pytest.mark.parametrize("status", [200, 302])
def test_real_transport_stack_disables_environment_proxy_discovery_and_redirects(tmp_path, monkeypatch, status):
    path, binding = credential(tmp_path)
    requests = []

    def fake_https(handler, request):
        assert handler._context.verify_mode == ssl.CERT_REQUIRED and handler._context.check_hostname
        requests.append(request)
        headers = Message()
        headers["Location"] = "https://untrusted.invalid/capture"
        response = urllib.response.addinfourl(io.BytesIO(FakeTransport().body), headers, request.full_url, status)
        response.msg = "synthetic response"
        return response

    class NoEnvironment:
        def get(self, key, default=None):
            if key not in {"SSL_CERT_FILE", "SSL_CERT_DIR", "SSLKEYLOGFILE"}:
                raise AssertionError("Request inspected provider, HOME or proxy environment")
            return default

        def __contains__(self, key):
            self.get(key)
            return False

    def no_proxies():
        raise AssertionError("Request attempted proxy discovery")

    with monkeypatch.context() as guard:
        guard.setattr(client, "_urlopen", _ORIGINAL_SEND)
        guard.setattr(client.os, "environ", NoEnvironment())
        guard.setattr(urllib.request, "getproxies", no_proxies)
        guard.setattr(urllib.request.HTTPSHandler, "https_open", fake_https)
        if status == 200:
            assert ask(path, binding, None) == "synthetic response"
        else:
            with pytest.raises(BackendError) as error:
                ask(path, binding, None)
            assert error.value.code == "ai_request_failed"
    assert len(requests) == 1 and requests[0].full_url == client.DEFAULT_ENDPOINT
