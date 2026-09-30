"""Outbound path redaction preserves useful language; transport stays synthetic."""

import json

import pytest

from tests.test_ai_intent_copilot import FakeTransport, message_text
from xfinaudio.ai.intent_copilot import extract_intent
from xfinaudio.ai.privacy import redact_paths
from xfinaudio.library.models import TrackRecord


@pytest.mark.parametrize(
    "path",
    ["/Users/Freddy/Music/Private Set.wav", r"C:\Users\Freddy\Private Set.wav", "~/Music/song.mp3", "../secret.wav"],
)
def test_embedded_paths_redacted_without_discarding_musical_request(path):
    result = redact_paths(f'Find house from "{path}" with energy 4-7')
    assert path not in result
    assert result == 'Find house from "[private path]" with energy 4-7'


def test_known_paths_with_spaces_redacted_and_ordinary_slashes_preserved():
    path = "/some unusual/track without suffix"
    assert redact_paths(f"house {path} energy 5", [path]) == "house [private path] energy 5"
    assert redact_paths("funk/soul at 120/128 bpm, key 8A") == "funk/soul at 120/128 bpm, key 8A"


@pytest.mark.parametrize(
    "path", ["/Users/Freddy/Private Music/Secret.wav", r"C:\Users\Freddy\Private Music\Secret.wav"]
)
def test_intent_redacts_paths_in_request_genres_and_opt_in_titles(monkeypatch, tmp_path, path):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-never-live")
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent"))
    track = TrackRecord(path=path, title=path, genre=f"House {path}")
    transport = FakeTransport(json.dumps({"name": "House", "target_track_count": 4}))
    extract_intent(f"four house tracks like {path}", [track], include_track_titles=True, transport=transport)
    prompt = message_text(transport)
    assert path not in prompt
    assert isinstance(transport.request.data, bytes)
    assert path not in json.loads(transport.request.data)["messages"][1]["content"]
    assert "Private Music" not in prompt
    assert "four house tracks like" in prompt
    assert "House" in prompt


def test_default_intent_also_redacts_malicious_genre(monkeypatch):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-never-live")
    path = "/Users/Freddy/Music/song.mp3"
    transport = FakeTransport('{"name":"safe","target_track_count":4}')
    extract_intent("house", [TrackRecord(path=path, genre=path)], transport=transport)
    assert path not in message_text(transport)
