"""Offline contract tests for the natural-language intent copilot.

Every test injects a fake transport, so the suite never opens a socket and never
needs a real ``NAN_API_KEY``. The fake records the outgoing request so the
payload, prompt, model and timeout stay pinned by assertions.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

import pytest

from xfinaudio.ai import NanConfigError, extract_intent
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.strategies import available_strategies

API_KEY = "nan-key-value-that-must-never-leak"


class FakeResponse:
    """Minimal stand-in for the object ``urlopen`` returns."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


class FakeTransport:
    """Record the request and return a completion body wrapping ``content``."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[float | None] = []

    def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        return FakeResponse(completion_body(self.content))

    @property
    def request(self) -> urllib.request.Request:
        assert self.requests, "the transport was never called"
        return self.requests[0]


def completion_body(content: str) -> bytes:
    payload = {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}}]}
    return json.dumps(payload).encode("utf-8")


def message_text(transport: FakeTransport) -> str:
    """Join every chat message so a prompt assertion can search the whole prompt."""
    data = transport.request.data
    assert data is not None, "the request carried no body"
    decoded = json.loads(data.decode("utf-8"))
    messages: list[dict[str, str]] = decoded["messages"]
    return "\n".join(message["content"] for message in messages)


def track(path: str, title: str, genre: str) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        genre=genre,
        bpm=122.0,
        camelot_key="8A",
        energy_level=5,
    )


def make_tracks() -> list[TrackRecord]:
    return [
        track("/Music/a.wav", "Amanecer En Tokyo", "Melodic Techno"),
        track("/Music/b.wav", "Neon Condor", "Melodic Techno"),
        track("/Music/c.wav", "Pampa Deep", "Progressive House"),
    ]


def fenced(payload: dict[str, Any]) -> str:
    return "```json\n" + json.dumps(payload) + "\n```"


@pytest.fixture
def ai_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Enable the flag, provide a key, and never touch the operator env file."""
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", API_KEY)
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent-from-fixture.env"))


def test_extract_intent_refuses_to_run_while_the_flag_is_off(monkeypatch: pytest.MonkeyPatch, ai_env: None) -> None:
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    transport = FakeTransport("{}")

    with pytest.raises(NanConfigError) as excinfo:
        extract_intent("build a melodic set", make_tracks(), transport=transport)

    assert "XFINAUDIO_AI_ENABLED" in str(excinfo.value)
    assert transport.requests == [], "a disabled copilot must never reach the transport"


def test_extract_intent_maps_fenced_json_to_a_validated_intent(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "Melodic voyage",
                "strategy": "harmonic_journey",
                "target_track_count": 12,
                "genre_focus": "melodic techno",
                "start_title": "Amanecer En Tokyo",
            }
        )
    )

    intent = extract_intent("viaje melodico de 12 temas", make_tracks(), transport=transport)

    assert intent.name == "Melodic voyage"
    assert intent.strategy == "harmonic_journey"
    assert intent.target_track_count == 12
    assert intent.genre_focus == "Melodic Techno"
    assert intent.start_path == "/Music/a.wav"
    assert intent.end_path is None


def test_extract_intent_maps_genre_to_the_library_exact_casing(ai_env: None) -> None:
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 8, "genre_focus": "PROGRESSIVE HOUSE"})
    )

    intent = extract_intent("progressive house set", make_tracks(), transport=transport)

    assert intent.genre_focus == "Progressive House"


def test_extract_intent_drops_a_genre_absent_from_the_library(ai_env: None) -> None:
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 8, "genre_focus": "Trance"})
    )

    intent = extract_intent("trance set", make_tracks(), transport=transport)

    assert intent.genre_focus is None


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        ("unknown_strategy", "harmonic_journey"),
        ("PEAK_TIME", "peak_time"),
        ("peak time", "peak_time"),
        ("Peak Time", "peak_time"),
    ],
)
def test_extract_intent_normalizes_strategy_case_insensitively(ai_env: None, requested: str, expected: str) -> None:
    transport = FakeTransport(
        fenced({"name": "set", "strategy": requested, "target_track_count": 8, "genre_focus": None})
    )

    intent = extract_intent("set", make_tracks(), transport=transport)

    assert intent.strategy == expected


def test_extract_intent_omits_paths_for_titles_absent_from_the_library(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "start_title": "A Song That Does Not Exist",
                "end_title": "Another Missing Track",
            }
        )
    )

    intent = extract_intent("set", make_tracks(), transport=transport)

    assert intent.start_path is None
    assert intent.end_path is None


def test_extract_intent_matches_titles_case_insensitively(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "start_title": "amanecer en tokyo",
                "end_title": "PAMPA DEEP",
            }
        )
    )

    intent = extract_intent("set", make_tracks(), transport=transport)

    assert intent.start_path == "/Music/a.wav"
    assert intent.end_path == "/Music/c.wav"


def test_extract_intent_sets_only_the_end_path_when_only_end_title_is_given(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "end_title": "Neon Condor",
            }
        )
    )

    intent = extract_intent("set", make_tracks(), transport=transport)

    assert intent.start_path is None
    assert intent.end_path == "/Music/b.wav"


def test_extract_intent_rejects_invalid_json_with_a_bounded_message(ai_env: None) -> None:
    raw = "the model refused to answer " * 40
    transport = FakeTransport(raw)

    with pytest.raises(ValueError) as excinfo:
        extract_intent("set", make_tracks(), transport=transport)

    message = str(excinfo.value)
    assert API_KEY not in message
    assert API_KEY not in repr(excinfo.value)
    assert len(message) < 300, "the error must echo at most a bounded snippet"
    assert raw not in message, "the full raw response must never be echoed"


def test_extract_intent_rejects_a_schema_violation_with_a_bounded_message(ai_env: None) -> None:
    # target_track_count below the Field(ge=2) floor is a pydantic failure.
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 1, "genre_focus": None})
    )

    with pytest.raises(ValueError) as excinfo:
        extract_intent("set", make_tracks(), transport=transport)

    message = str(excinfo.value)
    assert API_KEY not in message
    assert API_KEY not in repr(excinfo.value)


def test_extract_intent_passes_model_and_timeout_through_the_transport(ai_env: None) -> None:
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 8, "genre_focus": None})
    )

    extract_intent("set", make_tracks(), model="glm5.3-flash", timeout=90.0, transport=transport)

    assert transport.timeouts == [90.0]
    data = json.loads(transport.request.data.decode("utf-8"))
    assert data["model"] == "glm5.3-flash"


def test_extract_intent_prompt_lists_the_tracks_and_the_strategy_names(ai_env: None) -> None:
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 8, "genre_focus": None})
    )

    extract_intent("set", make_tracks(), transport=transport)

    prompt = message_text(transport)
    for library_track in make_tracks():
        assert library_track.title is not None
        assert library_track.genre is not None
        assert library_track.title in prompt
        assert library_track.genre in prompt
    for strategy_name in available_strategies():
        assert strategy_name in prompt


def test_extract_intent_respects_the_explicit_genre_vocabulary(ai_env: None) -> None:
    # The override, not the library, owns the vocabulary: "melodic house" is not
    # a library genre, yet the override maps it to its exact casing.
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 8, "genre_focus": "melodic house"})
    )

    intent = extract_intent(
        "melodic house set",
        make_tracks(),
        transport=transport,
        genre_vocabulary=["Melodic House", "Organic House"],
    )

    assert intent.genre_focus == "Melodic House"


def test_extract_intent_genre_vocabulary_drops_a_library_genre_it_does_not_contain(ai_env: None) -> None:
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 8, "genre_focus": "Progressive House"})
    )

    intent = extract_intent(
        "progressive house set",
        make_tracks(),
        transport=transport,
        genre_vocabulary=["Melodic House"],
    )

    assert intent.genre_focus is None


def test_extract_intent_prompt_documents_the_v2_intent_fields(ai_env: None) -> None:
    transport = FakeTransport(
        fenced({"name": "set", "strategy": "build", "target_track_count": 8, "genre_focus": None})
    )

    extract_intent("set", make_tracks(), transport=transport)

    prompt = message_text(transport)
    assert '"target_minutes": number between 5 and 600 or null' in prompt
    assert '"slot_role": one of ["warmup", "peak_time", "chill"] or null' in prompt
    assert "target_minutes is the number of minutes the set must fill" in prompt
    assert "slot_role is the arc curve for the set's role in the night" in prompt
    assert "independent of the ordering strategy" in prompt


def test_extract_intent_fills_target_minutes_and_slot_role(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "Closing set",
                "strategy": "build",
                "target_track_count": 12,
                "genre_focus": None,
                "target_minutes": 90,
                "slot_role": "chill",
            }
        )
    )

    intent = extract_intent("set de cierre de 90 minutos", make_tracks(), transport=transport)

    assert intent.target_minutes == 90.0
    assert intent.slot_role == "chill"


def test_extract_intent_accepts_a_numeric_string_for_target_minutes(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "target_minutes": "120",
            }
        )
    )

    intent = extract_intent("two hour set", make_tracks(), transport=transport)

    assert intent.target_minutes == 120.0


def test_extract_intent_drops_an_unknown_slot_role(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "slot_role": "afterhours",
            }
        )
    )

    intent = extract_intent("afterhours set", make_tracks(), transport=transport)

    assert intent.slot_role is None


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        ("WARMUP", "warmup"),
        ("peak time", "peak_time"),
        ("Peak Time", "peak_time"),
        ("peak-time", "peak_time"),
        ("  chill  ", "chill"),
    ],
)
def test_extract_intent_normalizes_slot_role_case_and_separators(
    ai_env: None, requested: str, expected: str
) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "slot_role": requested,
            }
        )
    )

    intent = extract_intent("set", make_tracks(), transport=transport)

    assert intent.slot_role == expected


@pytest.mark.parametrize("value", [601, 0, -5])
def test_extract_intent_rejects_an_out_of_range_target_minutes(ai_env: None, value: float) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "target_minutes": value,
            }
        )
    )

    with pytest.raises(ValueError) as excinfo:
        extract_intent("set", make_tracks(), transport=transport)

    message = str(excinfo.value)
    assert API_KEY not in message
    assert API_KEY not in repr(excinfo.value)
    assert len(message) < 300, "the error must echo at most a bounded snippet"


def test_extract_intent_keeps_the_v2_fields_null_by_default(ai_env: None) -> None:
    transport = FakeTransport(
        fenced(
            {
                "name": "set",
                "strategy": "build",
                "target_track_count": 8,
                "genre_focus": None,
                "target_minutes": None,
                "slot_role": None,
            }
        )
    )

    intent = extract_intent("set", make_tracks(), transport=transport)

    assert intent.target_minutes is None
    assert intent.slot_role is None
