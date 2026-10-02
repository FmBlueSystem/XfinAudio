"""Transport exceptions must not expose credentials to any AI workflow."""

import urllib.error

import pytest

from xfinaudio.ai.nan_client import NanConfigError, NanRequestError, chat


@pytest.mark.parametrize(
    "failure",
    [urllib.error.URLError("SYNTHETIC-SECRET"), OSError("SYNTHETIC-SECRET"), ValueError("SYNTHETIC-SECRET")],
)
def test_exception_details_do_not_cross_adapter_boundary(monkeypatch, failure):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "SYNTHETIC-SECRET")
    monkeypatch.setenv("NAN_API_BASE", "https://provider.invalid/chat")

    def send(*args, **kwargs):
        raise failure

    with pytest.raises((NanRequestError, NanConfigError)) as caught:
        chat("synthetic", transport=send)
    assert "SYNTHETIC-SECRET" not in str(caught.value)
    assert caught.value.__suppress_context__
