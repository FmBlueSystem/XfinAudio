"""Offline contract tests for the AI set narrative service.

Every test injects a fake transport, so the suite never opens a socket and never
needs a real ``NAN_API_KEY``. The fake records the outgoing request so the
payload, facts prompt, model and timeout stay pinned by assertions.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from xfinaudio.ai import NanConfigError, NanRequestError, narrate_set
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import ScoringWeights, TransitionScore
from xfinaudio.recommendation.strategies import PlaylistStrategy

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

    def __init__(self, content: str = "El set sube de energia.") -> None:
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


def track(path: str, title: str, *, bpm: float, key: str, energy: int, artist: str = "Test Artist") -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=artist,
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        metadata_status="complete",
    )


def make_tracks() -> list[TrackRecord]:
    return [
        track("/Music/a.wav", "Amanecer En Tokyo", bpm=118.0, key="8A", energy=4),
        track("/Music/b.wav", "Neon Condor", bpm=124.0, key="9A", energy=7),
        track("/Music/c.wav", "Pampa Deep", bpm=130.0, key="10A", energy=9),
    ]


def make_recommendation(tracks: list[TrackRecord] | None = None) -> PlaylistRecommendation:
    ordered = make_tracks() if tracks is None else tracks
    transitions = [
        TransitionScore(
            left_path=ordered[index].path,
            right_path=ordered[index + 1].path,
            total_score=0.72,
            component_scores={"harmonic": 0.9},
            explanations=[],
            warnings=[f"BPM jump between {ordered[index].title} and {ordered[index + 1].title}"],
        )
        for index in range(len(ordered) - 1)
    ]
    return PlaylistRecommendation(
        ordered_tracks=ordered,
        transition_scores=transitions,
        strategy=PlaylistStrategy(
            name="harmonic_journey",
            display_name="Harmonic Journey",
            description="Test strategy",
            weights=ScoringWeights(),
        ),
        warnings=["Energy arc dips twice"],
        applied_controls={},
        optimizer="test-optimizer",
        total_score=1.44,
    )


def make_readiness() -> DjReadinessReport:
    return DjReadinessReport(
        status="needs_review",
        summary="Needs Review — 0 blocker(s), 2 review item(s); max BPM jump 5.08%",
        checks=[
            DjReadinessCheck(label="Metadata", status="needs_review", detail="Two tracks miss energy"),
            DjReadinessCheck(label="Playlist size", status="ready", detail="Three tracks is a full set"),
        ],
        blocker_count=0,
        review_count=2,
    )


@pytest.fixture
def ai_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Enable the flag, provide a key, and never touch the operator env file."""
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", API_KEY)
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent-from-fixture.env"))


def test_narrate_set_refuses_to_run_while_the_flag_is_off(monkeypatch: pytest.MonkeyPatch, ai_env: None) -> None:
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    transport = FakeTransport()

    with pytest.raises(NanConfigError) as excinfo:
        narrate_set(make_recommendation(), make_readiness(), transport=transport)

    assert "XFINAUDIO_AI_ENABLED" in str(excinfo.value)
    assert transport.requests == [], "a disabled narrator must never reach the transport"


def test_narrate_set_without_tracks_refuses_before_the_transport(ai_env: None) -> None:
    transport = FakeTransport()

    with pytest.raises(ValueError, match="nothing to narrate"):
        narrate_set(make_recommendation(tracks=[]), make_readiness(), transport=transport)

    assert transport.requests == [], "an empty set must never reach the transport"


def test_narrate_set_returns_the_model_text_verbatim(ai_env: None) -> None:
    transport = FakeTransport(content="  El set abre calmo y cierra arriba.  ")

    narrative = narrate_set(make_recommendation(), make_readiness(), transport=transport)

    assert narrative == "  El set abre calmo y cierra arriba.  "


def test_narrate_set_prompt_carries_only_engine_facts(ai_env: None) -> None:
    transport = FakeTransport()

    narrate_set(make_recommendation(), make_readiness(), transport=transport)

    prompt = message_text(transport)
    for library_track in make_tracks():
        assert library_track.title is not None
        assert library_track.title in prompt
        assert library_track.camelot_key is not None
        assert library_track.camelot_key in prompt
        assert str(library_track.energy_level) in prompt
    assert "BPM jump between Amanecer En Tokyo and Neon Condor" in prompt
    assert "Needs Review — 0 blocker(s), 2 review item(s)" in prompt
    assert "2 review item(s)" in prompt
    assert "test-optimizer" in prompt


def test_narrate_set_prompt_bounds_the_response_and_forbids_invention(ai_env: None) -> None:
    transport = FakeTransport()

    narrate_set(make_recommendation(), make_readiness(), transport=transport)

    prompt = message_text(transport)
    lowered = prompt.lower()
    assert "150" in prompt, "the length guidance must be explicit"
    assert "only" in lowered
    assert "invent" in lowered or "make up" in lowered
    assert "español rioplatense" in lowered or "rioplatense" in lowered


def test_narrate_set_passes_model_and_timeout_through_the_transport(ai_env: None) -> None:
    transport = FakeTransport()

    narrate_set(make_recommendation(), make_readiness(), model="glm5.3-flash", timeout=90.0, transport=transport)

    assert transport.timeouts == [90.0]
    data = json.loads(transport.request.data.decode("utf-8"))
    assert data["model"] == "glm5.3-flash"


def test_narrate_set_uses_the_default_timeout_for_heavy_models(ai_env: None) -> None:
    transport = FakeTransport()

    narrate_set(make_recommendation(), make_readiness(), transport=transport)

    assert transport.timeouts == [120.0]


def test_narrate_set_maps_http_errors_to_a_bounded_request_error(ai_env: None) -> None:
    def failing(request: Any, timeout: float | None = None) -> Any:
        raise urllib.error.HTTPError(request.full_url, 429, API_KEY, {}, None)  # type: ignore[arg-type]

    with pytest.raises(NanRequestError) as excinfo:
        narrate_set(make_recommendation(), make_readiness(), transport=failing)

    message = str(excinfo.value)
    assert API_KEY not in message
    assert API_KEY not in repr(excinfo.value)
    assert "429" in message


def test_narrate_set_maps_timeouts_to_a_bounded_request_error(ai_env: None) -> None:
    def failing(request: Any, timeout: float | None = None) -> Any:
        raise TimeoutError("timed out")

    with pytest.raises(NanRequestError) as excinfo:
        narrate_set(make_recommendation(), make_readiness(), timeout=45.0, transport=failing)

    message = str(excinfo.value)
    assert API_KEY not in message
    assert API_KEY not in repr(excinfo.value)
    assert "45s" in message


def test_narrate_set_marks_missing_metadata_as_unknown_never_a_number(ai_env: None) -> None:
    """A fact the engine does not have must read as unknown, not as a guess."""
    track = TrackRecord(path="/Music/x.wav", title="Track Without Metadata", artist=None, metadata_status="incomplete")
    transport = FakeTransport()

    narrate_set(make_recommendation(tracks=[track]), make_readiness(), transport=transport)

    prompt = message_text(transport)
    assert "Track Without Metadata" in prompt
    assert "(unknown artist)" in prompt
    assert "BPM unknown" in prompt
    assert "energy unknown" in prompt


def test_narrate_set_says_so_when_no_transition_carries_a_warning(ai_env: None) -> None:
    recommendation = make_recommendation().model_copy(
        update={
            "transition_scores": [
                transition.model_copy(update={"warnings": []}) for transition in make_recommendation().transition_scores
            ]
        }
    )
    transport = FakeTransport()

    narrate_set(recommendation, make_readiness(), transport=transport)

    prompt = message_text(transport)
    assert "Transition warnings:" in prompt
    assert "- none" in prompt
    assert "BPM jump between" not in prompt


def test_narrate_set_takes_the_readiness_counts_from_the_report(ai_env: None) -> None:
    readiness = make_readiness().model_copy(update={"status": "blocked", "blocker_count": 1, "review_count": 3})
    transport = FakeTransport()

    narrate_set(make_recommendation(), readiness, transport=transport)

    prompt = message_text(transport)
    assert "status: blocked" in prompt
    assert "blockers: 1" in prompt
    assert "review items: 3" in prompt


def test_narrate_set_sends_the_constraints_as_the_system_message(ai_env: None) -> None:
    """The facts are the user message; the rules must travel as the system prompt."""
    transport = FakeTransport()

    narrate_set(make_recommendation(), make_readiness(), transport=transport)

    data = transport.request.data
    assert data is not None
    messages = json.loads(data.decode("utf-8"))["messages"]
    assert [message["role"] for message in messages] == ["system", "user"]
    system_message, user_message = messages
    assert "DJ set analyst" in system_message["content"]
    assert "DJ set analyst" not in user_message["content"]
    assert "Set facts" in user_message["content"]


def test_narrate_set_uses_anonymous_label_for_removed_track_warning(ai_env: None) -> None:
    """A warning can reference a track that is no longer in the set; it must still render."""
    recommendation = make_recommendation().model_copy(
        update={
            "transition_scores": [
                TransitionScore(
                    left_path="/Music/removed.wav",
                    right_path="/Music/a.wav",
                    total_score=0.5,
                    component_scores={},
                    explanations=[],
                    warnings=["Track was removed from the playlist"],
                )
            ]
        }
    )
    transport = FakeTransport()

    narrate_set(recommendation, make_readiness(), transport=transport)

    prompt = message_text(transport)
    assert "(unavailable track) -> Amanecer En Tokyo" in prompt
    assert "/Music/removed.wav" not in prompt
    assert "Track was removed from the playlist" in prompt


def test_narration_includes_actual_scores_and_readiness_checks_without_paths(ai_env: None) -> None:
    recommendation = make_recommendation()
    first = recommendation.transition_scores[0].model_copy(
        update={
            "explanations": ["harmonic compatibility 0.90"],
            "warnings": ["Missing: /Music/a.wav", "Unknown /private/elsewhere.wav"],
        }
    )
    recommendation = recommendation.model_copy(update={"transition_scores": [first]})
    readiness = make_readiness().model_copy(update={"summary": "Review /Music/a.wav"})
    transport = FakeTransport()
    narrate_set(recommendation, readiness, transport=transport)
    prompt = message_text(transport)
    assert "score 0.72" in prompt
    assert "harmonic compatibility 0.90" in prompt
    assert "Two tracks miss energy" in prompt
    assert "/Music" not in prompt
    assert "/private" not in prompt
