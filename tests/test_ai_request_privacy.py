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


def test_known_paths_redact_when_adjacent_to_words_or_wrapped_in_metadata():
    path = "/Users/Private/Music/song.wav"
    assert redact_paths(f"prefix{path}suffix house", [path]) == "prefix[private path]suffix house"


def test_known_windows_path_matching_is_case_insensitive():
    path = r"C:\Users\Private\Song.wav"
    assert redact_paths(f"prefix{path.lower()}suffix", [path]) == "prefix[private path]suffix"


def test_known_windows_paths_are_redacted_before_json_genre_escaping(monkeypatch):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-only")
    path = r"C:\Users\Private\Song.wav"
    transport = FakeTransport('{"name":"safe","target_track_count":4}')
    extract_intent("four tracks", [TrackRecord(path=path, genre=f"prefix{path}suffix")], transport=transport)
    assert "Private" not in message_text(transport)


def test_narrator_redacts_unrelated_paths_with_spaces_without_losing_engine_facts(monkeypatch):
    from tests.test_ai_set_narrator import make_readiness, make_recommendation
    from xfinaudio.ai.set_narrator import narrate_set

    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-only")
    recommendation = make_recommendation()
    unknown_path = "/Different Private Folder/Hidden Song.wav"
    readiness = make_readiness().model_copy(update={"summary": f"Review '{unknown_path}' while BPM remains 124"})
    transport = FakeTransport("Review the local evidence.")
    narrate_set(recommendation, readiness, transport=transport)
    prompt = message_text(transport)
    assert "Hidden Song" not in prompt
    assert "Different Private" not in prompt
    assert "while BPM remains 124" in prompt
    assert "1.44" in prompt


@pytest.mark.parametrize("path", ["/Users/Private/song.wav", r"C:\Users\Private\song.wav", "/Volumes/Private/song.wav"])
def test_recognizable_paths_embedded_in_text_are_redacted_even_without_library_context(path):
    result = redact_paths(f"prefix{path}suffix with house energy 5")
    assert "Private" not in result
    assert "with house energy 5" in result


@pytest.mark.parametrize(
    "path",
    [
        "Music/Private Client Set.wav",
        r"Music\Private Client Set.wav",
        "Music/Client/Private Set.aiff",
        "Música/Private Client Set.FLAC",
        '"Private Music/Private Client Set.wav"',
        r"'Private Music\Private Client Set.wav'",
    ],
)
def test_editor_transport_redacts_relative_audio_paths(monkeypatch, tmp_path, path):
    from xfinaudio.ai.structured_assists import interpret_editor_request

    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-never-live")
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent"))
    transport = FakeTransport('{"operation":"rising_energy"}')
    result = interpret_editor_request(f"raise energy using {path}, keep funk/soul at 120/128 bpm", transport=transport)
    prompt = message_text(transport)
    assert result.command == "raise energy"
    assert "Private" not in prompt and "Secret" not in prompt
    assert "[private path]" in prompt
    assert "raise energy using" in prompt
    assert "keep funk/soul at 120/128 bpm" in prompt


def test_relative_path_redaction_keeps_adjacent_musical_text():
    assert redact_paths("use Music/Song.mp3 then Other/Set.wav; house 120/128") == (
        "use [private path] then [private path]; house 120/128"
    )


def test_genre_and_ratio_before_relative_path_remain_musical_context():
    assert redact_paths("funk/soul at 120/128 bpm using Music/Private Song.wav") == (
        "funk/soul at 120/128 bpm using [private path]"
    )


def test_improvement_request_redacts_paths_and_sends_no_path_or_stable_id(monkeypatch, tmp_path):
    from tests.test_playlist_improvement import record, token_factory
    from xfinaudio.ai.structured_assists import interpret_improvement_request
    from xfinaudio.application.playlist_improvement import build_candidate_set, track_id

    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-never-live")
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent"))
    paths = ["/Users/Private/Music/one.wav", "/Users/Private/Music/two.wav"]
    records = [record(path, title=f"Song {index}", artist="Artist", genre="House") for index, path in enumerate(paths)]
    candidates = build_candidate_set(paths, records, token_source=token_factory())
    transport = FakeTransport(json.dumps({"orderedTrackIds": list(candidates.draft_tokens)}))
    result = interpret_improvement_request(f"reorder using {paths[0]} and keep house", candidates, transport=transport)
    assert result.orderedTrackIds == list(candidates.draft_tokens)
    prompt = message_text(transport)
    assert "Private" not in prompt
    assert "[private path]" in prompt
    assert paths[0] not in prompt
    assert track_id(paths[0]) not in prompt
    assert candidates.draft_tokens[0] in prompt
    assert "Song 0" in prompt
    # The only context the provider receives is the bounded display fields.
    context = json.loads(json.loads(transport.request.data.decode("utf-8"))["messages"][1]["content"])["context"]
    fields = {key for candidate in context["candidates"] for key in candidate}
    assert not fields & {"path", "id", "trackId", "sha256"}
