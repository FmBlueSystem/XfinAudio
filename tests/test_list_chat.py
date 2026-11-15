"""The assistant reads exactly the list facts and the conversation it is given."""

from __future__ import annotations

import io
import json

import pytest

from tests.test_headless_ai_context import setup as setup
from xfinaudio.ai import list_chat
from xfinaudio.ai.nan_client import request_context
from xfinaudio.quality.dj_readiness import DjReadinessCheck
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation


class ChatTransport:
    """A fake provider that records every request body and returns one reply."""

    def __init__(self, reply: str = "Sugerencia sintética sobre la lista."):
        self.reply = reply
        self.bodies: list[dict] = []

    def __call__(self, request, *, timeout):
        self.bodies.append(json.loads(request.data.decode("utf-8")))
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": self.reply}}]}).encode())


def review_of(backend):
    assert backend.review is not None
    return backend.review.recommendation, backend.review.readiness_report


def chat(facts: str, request: str = "¿Qué pista quitarías?", conversation=()):
    transport = ChatTransport()
    with request_context(enabled=True, key_provider=lambda: "dummy-test-only"):
        reply = list_chat.chat_with_list(facts, request, list(conversation), transport=transport)
    return reply, transport


def synthetic_recommendation(backend) -> PlaylistRecommendation:
    """The fixture review with one warning and an opening and closing control attached."""
    recommendation, _ = review_of(backend)
    transitions = list(recommendation.transition_scores)
    transitions[1] = transitions[1].model_copy(update={"warnings": ["Salto de energía alto"]})
    ordered = recommendation.ordered_tracks
    return recommendation.model_copy(
        update={
            "transition_scores": transitions,
            "applied_controls": {
                **recommendation.applied_controls,
                "start_path": ordered[0].path,
                "end_path": ordered[-1].path,
            },
        }
    )


def test_list_facts_render_every_track_field_for_every_position(setup):
    backend, _, root = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, list_chat.protected_positions(recommendation, []))
    tracks = recommendation.ordered_tracks
    assert "Pistas en orden de reproducción" in facts
    lines = [line for line in facts.splitlines() if any(line.startswith(f"{index}. ") for index in range(1, 9))]
    assert len(lines) == len(tracks)
    for index, (line, track) in enumerate(zip(lines, tracks, strict=True), start=1):
        assert line.startswith(f"{index}. {track.title} — {track.artist} | ")
        fields = line.split(" | ")
        assert len(fields) == 6
        assert fields[1] == track.genre
        assert fields[2] == f"BPM {track.bpm:g}"
        assert fields[3] == track.camelot_key
        assert fields[4] == f"energía {track.energy_level}"
        assert fields[5] == "0:02"
    # No file path and no opaque public track id ever reaches the prompt.
    assert str(root) not in facts
    for track in tracks:
        assert track.path not in facts
    assert "path" not in facts


def test_list_facts_describe_missing_values_instead_of_leaving_a_field_out(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    tracks = list(recommendation.ordered_tracks)
    tracks[0] = tracks[0].model_copy(
        update={"genre": None, "camelot_key": None, "bpm": None, "energy_level": None, "duration": None}
    )
    facts = list_chat.list_facts(
        recommendation.model_copy(update={"ordered_tracks": tracks}),
        readiness,
        {"opening": [], "closing": [], "required": []},
    )
    first = next(line for line in facts.splitlines() if line.startswith("1. "))
    assert first.split(" | ") == [
        f"1. {tracks[0].title} — {tracks[0].artist}",
        "sin dato",
        "BPM sin dato",
        "sin dato",
        "energía sin dato",
        "sin dato",
    ]


def test_list_facts_render_every_transition_with_score_explanations_and_warnings(setup):
    backend, _, _ = setup
    _, readiness = review_of(backend)
    recommendation = synthetic_recommendation(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    assert facts.count("- Transición ") == len(recommendation.transition_scores)
    for index, transition in enumerate(recommendation.transition_scores, start=1):
        line = next(item for item in facts.splitlines() if item.startswith(f"- Transición {index} "))
        assert f"(posición {index} → {index + 1})" in line
        assert f"puntuación {transition.total_score:.2f}" in line
        for explanation in transition.explanations:
            assert explanation in line
    warned = next(item for item in facts.splitlines() if item.startswith("- Transición 2 "))
    assert "avisos: Salto de energía alto" in warned
    quiet = next(item for item in facts.splitlines() if item.startswith("- Transición 1 "))
    assert "avisos: ninguno" in quiet


def test_list_facts_report_the_readiness_status_blockers_and_warnings(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    blocked = readiness.model_copy(
        update={
            "status": "blocked",
            "summary": "Lista bloqueada por metadatos",
            "blocker_count": 1,
            "review_count": 1,
            "checks": [
                DjReadinessCheck(label="Metadatos requeridos", status="blocked", detail="Falta la tonalidad"),
                DjReadinessCheck(label="Avisos de transición", status="needs_review", detail="Transiciones débiles"),
                DjReadinessCheck(label="Tamaño de la lista", status="ready", detail="Cuatro pistas"),
            ],
        }
    )
    facts = list_chat.list_facts(recommendation, blocked, {"opening": [], "closing": [], "required": []})
    assert "Preparación DJ" in facts
    assert "- estado: blocked" in facts
    assert "- resumen: Lista bloqueada por metadatos" in facts
    assert "- bloqueos: Falta la tonalidad" in facts
    assert "- avisos: Transiciones débiles" in facts
    assert "Cuatro pistas" not in facts


def test_list_facts_name_the_protected_opening_closing_and_required_positions(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    recommendation = synthetic_recommendation(backend)
    ordered = recommendation.ordered_tracks
    protected = list_chat.protected_positions(recommendation, [ordered[1].path, ordered[2].path, "/outside.flac"])
    facts = list_chat.list_facts(recommendation, readiness, protected)
    assert "Posiciones protegidas" in facts
    assert "- apertura: posición 1" in facts
    assert f"- cierre: posición {len(ordered)}" in facts
    assert "- obligatorias: posición 2, posición 3" in facts
    assert "/outside.flac" not in facts


def test_protected_positions_are_empty_for_an_unconstrained_list(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    protected = list_chat.protected_positions(recommendation, [])
    assert protected == {"opening": [], "closing": [], "required": []}
    facts = list_chat.list_facts(recommendation, readiness, protected)
    assert "- apertura: ninguna" in facts
    assert "- cierre: ninguna" in facts
    assert "- obligatorias: ninguna" in facts


def test_list_facts_never_carry_a_path_even_from_a_title_or_a_warning(setup):
    backend, _, root = setup
    recommendation, readiness = review_of(backend)
    target = root / "track-1.flac"
    tracks = list(recommendation.ordered_tracks)
    tracks[0] = tracks[0].model_copy(update={"title": f"Secret {target}"})
    transitions = list(recommendation.transition_scores)
    transitions[0] = transitions[0].model_copy(update={"warnings": [f"Missing file {target}"]})
    facts = list_chat.list_facts(
        recommendation.model_copy(update={"ordered_tracks": tracks, "transition_scores": transitions}),
        readiness,
        {"opening": [], "closing": [], "required": []},
    )
    assert str(target) not in facts and str(root) not in facts
    assert facts.count("[pista 1]") >= 2


def test_chat_with_list_sends_instructions_the_stored_conversation_and_the_new_message(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    reply, transport = chat(
        facts,
        request="¿Cómo mejoro la curva de energía?",
        conversation=[
            {"role": "user", "text": "¿qué transiciones son las más débiles?"},
            {"role": "assistant", "text": "La transición 2."},
        ],
    )
    assert reply == "Sugerencia sintética sobre la lista."
    messages = transport.bodies[0]["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1]["content"] == "¿Cómo mejoro la curva de energía?"
    assert messages[1]["content"] == "¿qué transiciones son las más débiles?"
    assert messages[2]["content"] == "La transición 2."
    system = messages[0]["content"]
    assert facts in system
    assert recommendation.ordered_tracks[0].title in system


def test_chat_instructions_ask_for_short_spanish_answers_and_concrete_suggestions(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    _, transport = chat(facts)
    system = transport.bodies[0]["messages"][0]["content"]
    for fragment in ("español", "250 palabras", "posición", "título", "quitar", "mover", "reemplazarla", "solo pistas"):
        assert fragment in system
    assert "no alcanzan" in system


@pytest.mark.parametrize("reply", ["", "   \n", "x" * 4001])
def test_chat_rejects_an_empty_or_oversized_reply(setup, reply):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    transport = ChatTransport(reply)
    with (
        request_context(enabled=True, key_provider=lambda: "dummy-test-only"),
        pytest.raises(ValueError),
    ):
        list_chat.chat_with_list(facts, "Pregunta", [], transport=transport)
    assert len(transport.bodies) == 1


def test_chat_accepts_a_reply_at_the_limit(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    transport = ChatTransport("x" * list_chat.MAX_REPLY_CHARS)
    with request_context(enabled=True, key_provider=lambda: "dummy-test-only"):
        assert list_chat.chat_with_list(facts, "Pregunta", [], transport=transport) == "x" * list_chat.MAX_REPLY_CHARS
