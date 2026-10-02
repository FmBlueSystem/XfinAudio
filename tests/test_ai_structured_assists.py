"""Actual Nan request contracts with exclusively synthetic transports."""

import json

import pytest

from tests.test_ai_intent_copilot import FakeTransport, message_text
from xfinaudio.ai.nan_client import NanConfigError, NanRequestError
from xfinaudio.ai.structured_assists import interpret_editor_request, interpret_library_query
from xfinaudio.library.models import TrackRecord


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-only")
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent"))


def test_library_calls_configured_chat_with_only_request_and_sanitized_genres():
    transport = FakeTransport('{"genre":"House","energy_min":2,"energy_max":5}')
    query = interpret_library_query(
        "house suitable for opening /Users/private/track.wav", ["House"], transport=transport
    )
    assert query.genre == "House"
    assert query.interpretation_note
    assert not query.matches(TrackRecord(path="unknown", genre="House"))
    assert query.matches(TrackRecord(path="known", genre="House", energy_level=3))
    assert "/Users/private" not in message_text(transport)
    assert isinstance(transport.request.data, bytes)
    body = json.loads(transport.request.data)
    assert body["model"]
    assert transport.timeouts == [30.0]
    assert transport.request.get_header("Authorization") == "Bearer synthetic-only"


@pytest.mark.parametrize(
    "raw",
    [
        '{"genre":"Invented"}',
        '{"genre":"House","path":"/secret"}',
        '{"energy_min":true}',
        '{"energy_min":"4"}',
        '{"energy_min":11}',
        '{"bpm_min":NaN}',
        '{"bpm_min":140,"bpm_max":100}',
        '{"key":"13A"}',
        '{"text":"' + "a" * 301 + '"}',
        '{"genre":"House","genre":"House"}',
        '```json\n{"genre":"House"}\n```',
        "[]",
        "{}",
        "null",
        "{" * 5000,
    ],
)
def test_library_rejects_invalid_untrusted_json_without_echo(raw):
    with pytest.raises(ValueError, match="AI interpretation") as error:
        interpret_library_query("find house", ["House"], transport=FakeTransport(raw))
    assert len(str(error.value)) < 180
    assert "/secret" not in str(error.value)


@pytest.mark.parametrize(
    ("response", "command"),
    [
        ({"operation": "shorten_tracks", "target": 10}, "shorten to 10 tracks"),
        ({"operation": "shorten_minutes", "target": 30}, "shorten to 30 minutes"),
        ({"operation": "rising_energy"}, "raise energy"),
        ({"operation": "falling_energy", "target": None}, "lower energy"),
    ],
)
def test_editor_returns_only_canonical_existing_engine_commands(response, command):
    transport = FakeTransport(json.dumps(response))
    result = interpret_editor_request("make a gradual climb", transport=transport, timeout=7)
    assert result.command == command
    assert transport.timeouts == [7]
    assert "Never select" in message_text(transport)


@pytest.mark.parametrize(
    "response",
    [
        {"operation": "delete_all"},
        {"operation": "shorten_tracks"},
        {"operation": "shorten_tracks", "target": 0},
        {"operation": "shorten_tracks", "target": True},
        {"operation": "shorten_minutes", "target": 601},
        {"operation": "shorten_tracks", "target": 1001},
        {"operation": "shorten_minutes", "target": 10.5},
        {"operation": "rising_energy", "target": 4},
        {"operation": "rising_energy", "paths": []},
    ],
)
def test_editor_rejects_unknown_actions_targets_and_path_commands(response):
    with pytest.raises(ValueError, match="AI interpretation"):
        interpret_editor_request("do it", transport=FakeTransport(json.dumps(response)))


@pytest.mark.parametrize("kind", ["disabled", "missing_key"])
def test_configuration_refuses_before_transport(monkeypatch, kind):
    if kind == "disabled":
        monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    else:
        monkeypatch.delenv("NAN_API_KEY")
    transport = FakeTransport("{}")
    with pytest.raises(NanConfigError):
        interpret_editor_request("raise energy", transport=transport)
    assert not transport.requests


def test_offline_error_is_safe_and_not_a_successful_interpretation():
    def offline(*args, **kwargs):
        raise OSError("private transport detail")

    with pytest.raises(NanRequestError) as error:
        interpret_library_query("house", ["House"], transport=offline)
    assert "private transport detail" not in str(error.value)


@pytest.mark.parametrize("user_request", ["", " " * 3, "a" * 2001])
def test_request_bound_is_checked_before_transport(user_request):
    transport = FakeTransport("{}")
    with pytest.raises(ValueError):
        interpret_editor_request(user_request, transport=transport)
    assert not transport.requests
