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


def chat(
    facts: str,
    request: str = "¿Qué pista quitarías?",
    conversation=(),
    *,
    track_count: int = 4,
    protected: tuple[int, ...] = (),
):
    transport = ChatTransport()
    with request_context(enabled=True, key_provider=lambda: "dummy-test-only"):
        answer = list_chat.chat_with_list(
            facts,
            request,
            list(conversation),
            track_count=track_count,
            protected=protected,
            transport=transport,
        )
    return answer, transport


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


def test_list_facts_report_the_requested_count_the_warnings_the_alternatives_and_the_hidden_library(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(
        recommendation,
        readiness,
        {"opening": [], "closing": [], "required": []},
        requested=20,
        warnings=["Track count shortfall: selected 4 of 20 requested tracks"],
        current_variant="balanced",
        alternatives=[
            {"name": "safe", "trackCount": 4, "qualityScore": 0.88},
            {"name": "balanced", "trackCount": 4, "qualityScore": 0.88},
            {"name": "adventurous", "trackCount": 20, "qualityScore": 0.77},
        ],
    )
    assert "Resumen de la generación" in facts
    assert "- pistas solicitadas: 20" in facts
    assert f"- pistas en la lista: {len(recommendation.ordered_tracks)}" in facts
    assert "- avisos del motor: Track count shortfall: selected 4 of 20 requested tracks" in facts
    assert "- variante actual: balanced" in facts
    assert "- otras alternativas: safe: 4 pistas, calidad 0.88; adventurous: 20 pistas, calidad 0.77" in facts
    assert "balanced: 4 pistas" not in facts
    assert "la biblioteca tiene más pistas que no puedes ver" in facts


def test_list_facts_state_the_generation_summary_even_when_it_is_not_given(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    assert "- pistas solicitadas: sin dato" in facts
    assert "- avisos del motor: ninguno" in facts
    assert "- otras alternativas: ninguna" in facts


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
    assert reply.reply == "Sugerencia sintética sobre la lista."
    assert reply.actions == () and reply.dropped == 0
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
        list_chat.chat_with_list(facts, "Pregunta", [], track_count=4, transport=transport)
    assert len(transport.bodies) == 1


def test_chat_accepts_a_reply_at_the_limit(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    transport = ChatTransport("x" * list_chat.MAX_REPLY_CHARS)
    with request_context(enabled=True, key_provider=lambda: "dummy-test-only"):
        answer = list_chat.chat_with_list(facts, "Pregunta", [], track_count=4, transport=transport)
    assert answer == list_chat.ChatAnswer("x" * list_chat.MAX_REPLY_CHARS, (), 0)


def structured(*items: dict, reply: str = "Propongo dos cambios.") -> str:
    return json.dumps({"reply": reply, "actions": list(items)})


def test_chat_instructions_ask_for_one_json_object_with_the_two_action_shapes(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    _, transport = chat(facts)
    system = transport.bodies[0]["messages"][0]["content"]
    assert "JSON" in system
    assert '"reply"' in system and '"actions"' in system
    assert '"type": "replace"' in system and '"type": "move"' in system
    assert "entre 0 y 5" in system
    assert "200" in system and "N = 4" in system
    assert '"type": "extend"' in system and '"type": "use_variant"' in system
    assert "mayor que el largo actual" in system and "100" in system
    assert '"variant": "adventurous"' in system
    assert "un solo extend y un solo use_variant" in system


def test_the_answer_is_read_as_a_json_object_with_its_valid_actions(setup):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    transport = ChatTransport(
        structured(
            {"type": "replace", "position": 3, "reason": "Baja energía"},
            {"type": "move", "position": 4, "to": 2, "reason": "Sube antes"},
        )
    )
    with request_context(enabled=True, key_provider=lambda: "dummy-test-only"):
        answer = list_chat.chat_with_list(facts, "Pregunta", [], track_count=4, transport=transport)
    assert answer.reply == "Propongo dos cambios."
    assert answer.actions == (
        list_chat.ProposedAction("replace", 3, None, "Baja energía"),
        list_chat.ProposedAction("move", 4, 2, "Sube antes"),
    )
    assert answer.dropped == 0
    assert [action.public() for action in answer.actions] == [
        {"type": "replace", "position": 3, "reason": "Baja energía"},
        {"type": "move", "position": 4, "to": 2, "reason": "Sube antes"},
    ]


@pytest.mark.parametrize(
    "raw",
    [
        "Quitaría la pista 3 y movería la 4 al cierre.",
        'Claro: {"reply": "Listo.", "actions": []}',
        '["no", "es", "un", "objeto"]',
        json.dumps({"actions": [{"type": "replace", "position": 1, "reason": "motivo"}]}),
        json.dumps({"reply": 7, "actions": []}),
    ],
)
def test_an_answer_that_is_not_the_structured_object_is_used_whole_as_the_reply(raw):
    answer = list_chat.parse_answer(raw, 4)
    assert answer.actions == () and answer.dropped == 0
    assert answer.reply == raw


def test_a_fenced_json_object_is_read_as_the_structured_answer():
    fence = "`" * 3
    raw = fence + "json\n" + structured({"type": "move", "position": 1, "to": 2, "reason": "motivo"}) + "\n" + fence
    answer = list_chat.parse_answer(raw, 4)
    assert answer.reply == "Propongo dos cambios."
    assert answer.actions == (list_chat.ProposedAction("move", 1, 2, "motivo"),)


@pytest.mark.parametrize(
    "item",
    [
        "no es un objeto",
        {"type": "remove", "position": 1, "reason": "motivo"},
        {"type": "replace", "position": 1, "reason": "motivo", "to": 2},
        {"type": "move", "position": 1, "reason": "motivo"},
        {"type": "move", "position": 1, "to": 2, "reason": "motivo", "path": "/private"},
        {"type": "replace", "position": 0, "reason": "motivo"},
        {"type": "replace", "position": 5, "reason": "motivo"},
        {"type": "replace", "position": "1", "reason": "motivo"},
        {"type": "replace", "position": True, "reason": "motivo"},
        {"type": "move", "position": 1, "to": 1, "reason": "motivo"},
        {"type": "move", "position": 1, "to": 0, "reason": "motivo"},
        {"type": "move", "position": 1, "to": 5, "reason": "motivo"},
        {"type": "move", "position": 1, "to": "2", "reason": "motivo"},
        {"type": "replace", "position": 1, "reason": "x" * 201},
        {"type": "replace", "position": 1, "reason": 7},
        {"type": "replace", "position": 3, "reason": "protegida"},
    ],
)
def test_an_action_that_cannot_apply_is_dropped_and_counted(item):
    answer = list_chat.parse_answer(structured(item), 4, (3,))
    assert answer.reply == "Propongo dos cambios."
    assert answer.actions == ()
    assert answer.dropped == 1


def test_every_dropped_action_reports_its_raw_value_and_the_reason():
    raw_items = [
        "no es un objeto",
        {"type": "remove", "position": 1, "reason": "motivo"},
        {"type": "replace", "position": 1, "reason": "motivo", "to": 2},
        {"type": "replace", "position": 9, "reason": "motivo"},
        {"type": "replace", "position": 1, "reason": "x" * 201},
        {"type": "replace", "position": 3, "reason": "protegida"},
        {"type": "move", "position": 2, "to": 2, "reason": "motivo"},
    ]
    raw = structured(*raw_items)
    answer = list_chat.parse_answer(raw, 4, (3,))
    assert answer.actions == () and answer.dropped == len(raw_items)
    assert answer.dropped_items == (
        list_chat.DroppedAction("no es un objeto", "unsupported change"),
        list_chat.DroppedAction(raw_items[1], "unsupported change"),
        list_chat.DroppedAction(raw_items[2], "unexpected fields"),
        list_chat.DroppedAction(raw_items[3], "position outside the list"),
        list_chat.DroppedAction(raw_items[4], "missing or oversized reason"),
        list_chat.DroppedAction(raw_items[5], "protected position"),
        list_chat.DroppedAction(raw_items[6], "target outside the list"),
    )
    assert [item.public() for item in answer.dropped_items][3] == {
        "raw": raw_items[3],
        "reason": "position outside the list",
    }
    assert answer.raw == raw
    repeated = structured(
        {"type": "replace", "position": 2, "reason": "motivo"},
        {"type": "move", "position": 2, "to": 1, "reason": "motivo"},
    )
    assert list_chat.parse_answer(repeated, 8).dropped_items == (
        list_chat.DroppedAction({"type": "move", "position": 2, "to": 1, "reason": "motivo"}, "repeated position"),
    )
    six = structured(*({"type": "replace", "position": index, "reason": "motivo"} for index in range(1, 7)))
    assert list_chat.parse_answer(six, 8).dropped_items == (
        list_chat.DroppedAction({"type": "replace", "position": 6, "reason": "motivo"}, "over the change limit"),
    )


def test_the_answer_is_read_with_the_extend_and_use_variant_shapes():
    answer = list_chat.parse_answer(
        structured(
            {"type": "extend", "to": 20, "reason": "Quedó corta"},
            {"type": "use_variant", "variant": "adventurous", "reason": "Más pistas"},
        ),
        8,
    )
    assert answer.actions == (
        list_chat.ProposedAction("extend", None, 20, "Quedó corta"),
        list_chat.ProposedAction("use_variant", None, None, "Más pistas", "adventurous"),
    )
    assert answer.dropped == 0
    assert [action.public() for action in answer.actions] == [
        {"type": "extend", "to": 20, "reason": "Quedó corta"},
        {"type": "use_variant", "variant": "adventurous", "reason": "Más pistas"},
    ]


@pytest.mark.parametrize(
    "item,reason",
    [
        ({"type": "extend", "to": 8, "reason": "motivo"}, "target outside the list"),
        ({"type": "extend", "to": 101, "reason": "motivo"}, "target outside the list"),
        ({"type": "extend", "to": "9", "reason": "motivo"}, "target outside the list"),
        ({"type": "extend", "to": True, "reason": "motivo"}, "target outside the list"),
        ({"type": "extend", "to": 9}, "unexpected fields"),
        ({"type": "extend", "to": 9, "reason": "motivo", "position": 1}, "unexpected fields"),
        ({"type": "extend", "to": 9, "reason": "x" * 201}, "missing or oversized reason"),
        ({"type": "use_variant", "variant": "wild", "reason": "motivo"}, "unsupported variant"),
        ({"type": "use_variant", "variant": 7, "reason": "motivo"}, "unsupported variant"),
        ({"type": "use_variant", "variant": "safe", "to": 6, "reason": "motivo"}, "unexpected fields"),
        ({"type": "use_variant", "variant": "safe", "reason": 7}, "missing or oversized reason"),
        ({"type": "use_variant", "variant": "safe", "reason": "x" * 201}, "missing or oversized reason"),
    ],
)
def test_an_extend_or_a_use_variant_that_cannot_apply_is_dropped_with_its_reason(item, reason):
    answer = list_chat.parse_answer(structured(item), 8)
    assert answer.actions == () and answer.dropped == 1
    assert answer.dropped_items == (list_chat.DroppedAction(item, reason),)


def test_only_one_extend_and_one_use_variant_are_kept_per_reply():
    raw = structured(
        {"type": "extend", "to": 10, "reason": "motivo"},
        {"type": "use_variant", "variant": "safe", "reason": "motivo"},
        {"type": "extend", "to": 12, "reason": "motivo"},
        {"type": "use_variant", "variant": "adventurous", "reason": "motivo"},
    )
    answer = list_chat.parse_answer(raw, 8)
    assert [action.type for action in answer.actions] == ["extend", "use_variant"]
    assert answer.dropped == 2
    assert [item.reason for item in answer.dropped_items] == ["repeated change type", "repeated change type"]


def test_a_repeated_position_and_actions_beyond_five_are_dropped_and_counted():
    repeated = structured(
        {"type": "replace", "position": 2, "reason": "motivo"},
        {"type": "move", "position": 2, "to": 1, "reason": "motivo"},
    )
    answer = list_chat.parse_answer(repeated, 8)
    assert answer.actions == (list_chat.ProposedAction("replace", 2, None, "motivo"),)
    assert answer.dropped == 1
    six = structured(*({"type": "replace", "position": index, "reason": "motivo"} for index in range(1, 7)))
    answer = list_chat.parse_answer(six, 8)
    assert [action.position for action in answer.actions] == [1, 2, 3, 4, 5]
    assert answer.dropped == 1


@pytest.mark.parametrize("reply", ["", "   ", "x" * (list_chat.MAX_REPLY_CHARS + 1)])
def test_the_reply_rule_still_applies_to_a_structured_reply(setup, reply):
    backend, _, _ = setup
    recommendation, readiness = review_of(backend)
    facts = list_chat.list_facts(recommendation, readiness, {"opening": [], "closing": [], "required": []})
    transport = ChatTransport(structured(reply=reply))
    with (
        request_context(enabled=True, key_provider=lambda: "dummy-test-only"),
        pytest.raises(ValueError),
    ):
        list_chat.chat_with_list(facts, "Pregunta", [], track_count=4, transport=transport)
    assert len(transport.bodies) == 1
