"""Actual Nan request contracts with exclusively synthetic transports."""

import json

import pytest

from tests.test_ai_intent_copilot import FakeTransport, message_text
from tests.test_playlist_improvement import record, records_for, token_factory
from xfinaudio.ai.nan_client import NanConfigError, NanRequestError
from xfinaudio.ai.structured_assists import (
    MAX_IMPROVEMENT_PAYLOAD_BYTES,
    ImprovementInterpretation,
    interpret_editor_request,
    interpret_improvement_request,
    interpret_library_query,
)
from xfinaudio.ai.structured_common import _POLICY, ask_object
from xfinaudio.application.playlist_improvement import MAX_DRAFT_TRACKS, build_candidate_set, track_id
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


# --- Editor improvement schema: strict token-only provider responses ---------


def improvement_candidates(*, start: int = 0, paths: list[str] | None = None, pool: list[str] | None = None):
    chosen = paths if paths is not None else ["a", "b", "c"]
    records = records_for([*chosen, *(pool or [])])
    return build_candidate_set(
        chosen,
        records,
        include_replacements=bool(pool),
        token_source=token_factory(start),
    )


def test_improvement_returns_the_validated_token_order_and_optional_rationale():
    candidates = improvement_candidates()
    ordered = [candidates.draft_tokens[2], candidates.draft_tokens[0], candidates.draft_tokens[1]]
    transport = FakeTransport(json.dumps({"orderedTrackIds": ordered, "rationale": "Smoother flow"}))
    result = interpret_improvement_request("smooth the flow", candidates, transport=transport, timeout=12)
    assert isinstance(result, ImprovementInterpretation)
    assert result.orderedTrackIds == ordered
    assert result.rationale == "Smoother flow"
    assert transport.timeouts == [12]


def test_improvement_accepts_a_response_without_rationale():
    candidates = improvement_candidates()
    transport = FakeTransport(json.dumps({"orderedTrackIds": list(candidates.draft_tokens)}))
    result = interpret_improvement_request("reorder", candidates, transport=transport)
    assert result.rationale is None


def test_improvement_prompt_replaces_the_shared_no_selection_policy():
    candidates = improvement_candidates()
    transport = FakeTransport(json.dumps({"orderedTrackIds": list(candidates.draft_tokens)}))
    interpret_improvement_request("reorder", candidates, transport=transport)
    prompt = message_text(transport)
    assert "Never select or order tracks" not in prompt
    assert "Select and order ONLY" in prompt
    assert "orderedTrackIds" in prompt


def test_ask_object_default_policy_stays_shared_and_unchanged():
    transport = FakeTransport("{}")
    ask_object("do it", {"genres": []}, "SCHEMA", transport=transport, timeout=3)
    system = message_text(transport).split("\n", 1)[0]
    assert system == _POLICY + "SCHEMA"
    assert "Select and order ONLY" not in system


def test_ask_object_opt_in_policy_is_replaced_for_that_call_only():
    transport = FakeTransport("{}")
    ask_object("do it", {}, "SCHEMA", transport=transport, timeout=3, policy="EDITOR POLICY ")
    system = message_text(transport).split("\n", 1)[0]
    assert system == "EDITOR POLICY SCHEMA"
    assert "Never select or order tracks" not in system


def test_legacy_editor_helper_still_receives_the_shared_policy():
    transport = FakeTransport('{"operation":"rising_energy"}')
    interpret_editor_request("raise energy", transport=transport)
    prompt = message_text(transport)
    assert "Never select or order tracks" in prompt
    assert "Select and order ONLY" not in prompt


def test_improvement_payload_sends_only_bounded_candidate_metadata():
    paths = ["/Users/Private/Music/one.wav", "/Users/Private/Music/two.wav"]
    records = [record(path, title=f"Song {index}", artist="Artist", genre="House") for index, path in enumerate(paths)]
    candidates = build_candidate_set(paths, records, token_source=token_factory())
    transport = FakeTransport(json.dumps({"orderedTrackIds": list(candidates.draft_tokens)}))
    interpret_improvement_request(f"reorder using {paths[0]}", candidates, transport=transport)
    prompt = message_text(transport)
    payload = json.loads(json.loads(transport.request.data.decode("utf-8"))["messages"][1]["content"])
    assert paths[0] not in prompt
    assert track_id(paths[0]) not in prompt
    assert "Private" not in prompt
    assert "[private path]" in prompt
    assert [entry["token"] for entry in payload["context"]["candidates"]] == list(candidates.draft_tokens)
    assert all("path" not in entry for entry in payload["context"]["candidates"])
    assert payload["context"]["candidates"][0]["title"] == "Song 0"


def test_improvement_payload_over_the_budget_fails_before_transport():
    paths = [f"p{index}" for index in range(MAX_DRAFT_TRACKS)]
    records = [record(path, title="t" * 400, artist="a" * 400, genre="g" * 100) for path in paths]
    candidates = build_candidate_set(paths, records, token_source=token_factory())
    transport = FakeTransport("{}")
    with pytest.raises(ValueError, match="too large"):
        interpret_improvement_request("reorder everything", candidates, transport=transport)
    assert not transport.requests
    assert MAX_IMPROVEMENT_PAYLOAD_BYTES == 32 * 1024


def test_improvement_request_bound_is_checked_before_transport():
    candidates = improvement_candidates()
    transport = FakeTransport("{}")
    with pytest.raises(ValueError):
        interpret_improvement_request("a" * 2001, candidates, transport=transport)
    assert not transport.requests


def test_improvement_accepts_the_bounded_maximum_order():
    paths = [f"d{index}" for index in range(MAX_DRAFT_TRACKS)]
    candidates = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    transport = FakeTransport(json.dumps({"orderedTrackIds": list(candidates.draft_tokens)}))
    result = interpret_improvement_request("reorder", candidates, transport=transport)
    assert len(result.orderedTrackIds) == MAX_DRAFT_TRACKS


def test_improvement_accepts_a_two_track_order():
    candidates = improvement_candidates()
    ordered = list(candidates.draft_tokens[:2])
    transport = FakeTransport(json.dumps({"orderedTrackIds": ordered}))
    assert interpret_improvement_request("reorder", candidates, transport=transport).orderedTrackIds == ordered


def test_improvement_accepts_authorized_replacement_tokens():
    candidates = improvement_candidates(paths=["a", "b"], pool=["p1", "p2"])
    ordered = [candidates.replacement_tokens[0], candidates.draft_tokens[0]]
    transport = FakeTransport(json.dumps({"orderedTrackIds": ordered}))
    assert interpret_improvement_request("replace a track", candidates, transport=transport).orderedTrackIds == ordered


def test_improvement_rejects_tokens_outside_the_authorized_candidate_set():
    candidates = improvement_candidates()
    raw = json.dumps({"orderedTrackIds": ["ffffffffffffffff", candidates.draft_tokens[0]]})
    with pytest.raises(ValueError, match="AI interpretation"):
        interpret_improvement_request("reorder", candidates, transport=FakeTransport(raw))


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "[]",
        "null",
        '{"orderedTrackIds": {}}',
        '{"orderedTrackIds": "0000000000000001"}',
        '{"orderedTrackIds": [1, 2]}',
        '{"orderedTrackIds": [true, false]}',
        '{"orderedTrackIds": []}',
        '{"orderedTrackIds": ["0000000000000001"]}',
        "{}",
        json.dumps({"orderedTrackIds": [f"{index:016x}" for index in range(1, 82)]}),
        '{"orderedTrackIds": ["000000000000000G", "0000000000000002"]}',
        '{"orderedTrackIds": ["/Users/private/song.wav", "0000000000000002"]}',
        '{"orderedTrackIds": ["' + "a" * 64 + '", "0000000000000002"]}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000001"]}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002", "unknown-key-here"]}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002"], "path": "/secret"}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002"], '
        '"orderedTrackIds": ["0000000000000003", "0000000000000004"]}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002"], "rationale": NaN}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002"], "rationale": "' + "r" * 401 + '"}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002"], "rationale": "bad\\u0000null"}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002"], "rationale": "/Users/private/song.wav"}',
        '{"orderedTrackIds": ["0000000000000001", "0000000000000002"], "rationale": "' + "r" * 5000 + '"}',
        "{" * 5000,
    ],
)
def test_improvement_rejects_malformed_untrusted_response_without_echo(raw):
    candidates = improvement_candidates()
    with pytest.raises(ValueError, match="AI interpretation") as error:
        interpret_improvement_request("reorder", candidates, transport=FakeTransport(raw))
    assert len(str(error.value)) < 180
    assert "/secret" not in str(error.value)
