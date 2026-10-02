"""Offline credential-boundary tests; every response is generated in memory."""

from __future__ import annotations

import io
import urllib.request
import urllib.response
from email.message import Message

import pytest

from xfinaudio.ai.nan_client import NanConfigError, NanRequestError, chat

ENDPOINT = "https://provider.invalid/v1/chat/completions"
KEY = "SYNTHETIC-TEST-ONLY"
BODY = b'{"choices":[{"message":{"content":"ok"}}]}'


@pytest.fixture(autouse=True)
def ai_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", KEY)
    monkeypatch.setenv("NAN_API_BASE", ENDPOINT)
    # Avoid a previously cached global urllib opener influencing the test.
    monkeypatch.setattr(urllib.request, "_opener", None)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://provider.invalid/v1/chat/completions",
        "file:///tmp/chat",
        "/v1/chat/completions",
        "https:///v1/chat/completions",
        f"https://user:{KEY}@provider.invalid/chat",
        "https://provider.invalid:invalid/chat",
        "https://provider.invalid:65536/chat",
        "https://provider.invalid/chat#fragment",
        "https://provider.invalid/\nchat",
        " https://provider.invalid/chat",
    ],
)
def test_unsafe_endpoint_fails_before_transport(monkeypatch: pytest.MonkeyPatch, endpoint: str) -> None:
    monkeypatch.setenv("NAN_API_BASE", endpoint)
    requests: list[urllib.request.Request] = []

    def fake_send(request: urllib.request.Request, **kwargs: object) -> io.BytesIO:
        requests.append(request)
        return io.BytesIO(BODY)

    with pytest.raises(NanConfigError, match="HTTPS") as error:
        chat("synthetic", transport=fake_send)
    assert requests == []
    assert KEY not in str(error.value)
    assert endpoint not in str(error.value)


def install_responses(
    monkeypatch: pytest.MonkeyPatch, *, status: int, location: str = ENDPOINT
) -> list[urllib.request.Request]:
    requests: list[urllib.request.Request] = []

    def fake_open(handler: object, request: urllib.request.Request) -> urllib.response.addinfourl:
        requests.append(request)
        headers: Message[str, str] = Message()
        headers["Location"] = location
        code = status if len(requests) == 1 else 200
        response = urllib.response.addinfourl(io.BytesIO(BODY), headers, request.full_url, code)
        response.msg = "synthetic response"
        return response

    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", fake_open)
    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", fake_open)
    return requests


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize(
    "location",
    [
        ENDPOINT + "/next",
        "https://other.invalid/capture",
        "https://provider.invalid:8443/capture",
        "http://provider.invalid/capture",
        "http://other.invalid/capture",
    ],
)
def test_default_transport_never_follows_redirects(monkeypatch: pytest.MonkeyPatch, status: int, location: str) -> None:
    requests = install_responses(monkeypatch, status=status, location=location)

    with pytest.raises(NanRequestError, match=f"HTTP status {status}") as error:
        chat("synthetic")

    assert len(requests) == 1, "a redirect destination must receive no request or credentials"
    assert requests[0].full_url == ENDPOINT
    assert KEY not in str(error.value)
    assert location not in str(error.value)


def test_default_transport_sends_authorization_only_on_original_successful_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = install_responses(monkeypatch, status=200)

    assert chat("synthetic") == "ok"
    assert len(requests) == 1
    request = requests[0]
    assert request.get_header("Authorization") == f"Bearer {KEY}"
    assert "Authorization" not in request.headers
    assert request.unredirected_hdrs["Authorization"] == f"Bearer {KEY}"
