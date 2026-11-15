"""The list conversation: consent, the exact messages, memory and its boundaries."""

from __future__ import annotations

import io
import json

import pytest

from tests.test_headless_ai_context import setup as setup
from xfinaudio.ai import nan_client
from xfinaudio.headless.common import BackendError
from xfinaudio.library.scan_service import ScanCancellationToken

QUESTION = "¿Qué pista quitarías y por qué?"
REPLY = "Quitaría la pista 3 y movería la 4 al cierre."


class ChatTransport:
    """Fake provider that records each body, timeout and reply in order."""

    def __init__(self, reply: str = REPLY):
        self.reply = reply
        self.bodies: list[dict] = []
        self.timeouts: list[float] = []
        self.on_send = lambda: None

    def __call__(self, request, *, timeout):
        self.bodies.append(json.loads(request.data.decode("utf-8")))
        self.timeouts.append(timeout)
        self.on_send()
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": self.reply}}]}).encode())


def forbidden(*args, **kwargs):
    raise AssertionError("Real provider requests are forbidden")


@pytest.fixture
def chat_setup(setup, monkeypatch):
    from xfinaudio.headless.optional_ai import OptionalAI

    monkeypatch.setattr(nan_client, "_urlopen", forbidden)
    backend, selectors, root = setup
    transport = ChatTransport()
    facade = OptionalAI(backend, transport=transport)
    credential_path = root.resolve().parent / "dummy-selected.env"
    credential_path.write_bytes(b"NAN_API_KEY=synthetic-test-only\n")
    credential_path.chmod(0o600)
    status = call(facade, "ai.status")
    selected = call(facade, "ai.credential.set", {"revision": status["revision"], "path": str(credential_path)})
    call(facade, "ai.settings.update", {"revision": selected["revision"], "enabled": True})
    return facade, transport, backend, selectors, root


def call(facade, method, params=None, *, token=None, emit=None):
    return facade.execute(method, params or {}, token or ScanCancellationToken(), emit or (lambda _: None))


def prepare(facade, review, request=QUESTION):
    return call(facade, "ai.prepare", {"surface": "chat", "request": request, "context": {"reviewId": review}})


def turn(facade, review, request=QUESTION, **kwargs):
    prepared = prepare(facade, review, request)
    return call(facade, "ai.run", {"previewId": prepared["previewId"], "confirmed": True}, **kwargs)


def history(facade):
    return call(facade, "ai.chat.history")


def current_review_id(backend):
    assert backend.review_id is not None
    return backend.review_id


def test_chat_prepare_discloses_the_list_and_marks_the_first_turn(chat_setup):
    facade, transport, backend, _, root = chat_setup
    preview = prepare(facade, current_review_id(backend))
    assert transport.bodies == []
    assert preview["surface"] == "chat" and preview["recipient"] == nan_client.DEFAULT_ENDPOINT
    assert preview["firstTurn"] is True and preview["requestPreview"] == QUESTION
    disclosure = " ".join(preview["disclosure"])
    assert "títulos" in disclosure and "Transiciones" in disclosure and "conversación" in disclosure
    assert "rutas" in disclosure and str(root) not in json.dumps(preview)


def test_chat_run_sends_the_system_message_and_returns_the_whole_conversation(chat_setup):
    facade, transport, backend, _, root = chat_setup
    result = turn(facade, current_review_id(backend))["result"]
    assert set(result) == {
        "resultId",
        "surface",
        "kind",
        "title",
        "text",
        "proposal",
        "canApply",
        "conversation",
        "listChanged",
        "actions",
        "droppedActions",
    }
    assert result["surface"] == "chat" and result["kind"] == "chat"
    assert result["text"] == REPLY and result["proposal"] is None and result["canApply"] is False
    assert result["actions"] == [] and result["droppedActions"] == 0
    assert result["conversation"] == [
        {"role": "user", "text": QUESTION},
        {"role": "assistant", "text": REPLY},
    ]
    assert result["listChanged"] is False
    assert transport.timeouts == [120]
    messages = transport.bodies[0]["messages"]
    assert [message["role"] for message in messages] == ["system", "user"]
    assert messages[-1]["content"] == QUESTION
    system = messages[0]["content"]
    assert "250 palabras" in system and "Transición 1" in system
    assert backend.review is not None
    assert backend.review.recommendation.ordered_tracks[0].title in system
    assert str(root) not in json.dumps(transport.bodies[0])


def test_chat_tells_the_assistant_the_requested_count_the_warnings_and_the_alternatives(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    backend.execute("prep.generate", {"targetTrackCount": 20, "name": "Lista corta"})
    turn(facade, current_review_id(backend))
    system = transport.bodies[0]["messages"][0]["content"]
    assert backend.plan is not None and backend.review is not None
    current = backend.review.variant_name
    assert "- pistas solicitadas: 20" in system
    assert f"- pistas en la lista: {len(backend.review.recommendation.ordered_tracks)}" in system
    assert "- avisos del motor: Track count shortfall: selected 8 of 20 requested tracks" in system
    assert f"- variante actual: {current}" in system
    others = [item for item in backend.review_actions.base["variants"] if item["name"] != current]
    assert others
    for variant in others:
        assert f"{variant['name']}: {variant['trackCount']} pistas, calidad {variant['qualityScore']:.2f}" in system
    assert "la biblioteca tiene más pistas que no puedes ver" in system


def test_chat_second_turn_carries_the_stored_conversation_and_keeps_consent(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    review = current_review_id(backend)
    turn(facade, review)
    preview = prepare(facade, review, request="¿Y cuál moverías?")
    assert preview["firstTurn"] is False
    answer = call(facade, "ai.run", {"previewId": preview["previewId"], "confirmed": True})["result"]
    messages = transport.bodies[1]["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == QUESTION and messages[2]["content"] == REPLY
    assert messages[3]["content"] == "¿Y cuál moverías?"
    assert answer["conversation"] == [
        {"role": "user", "text": QUESTION},
        {"role": "assistant", "text": REPLY},
        {"role": "user", "text": "¿Y cuál moverías?"},
        {"role": "assistant", "text": REPLY},
    ]
    assert answer["listChanged"] is False


def test_chat_reads_the_edited_list_and_reports_that_it_changed(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    turn(facade, current_review_id(backend))
    assert backend.review is not None
    details = backend.execute("review.details", {"reviewId": backend.review_id})
    track_ids = [track["id"] for track in details["tracks"]]
    edited = backend.execute("review.reorder", {"reviewId": details["reviewId"], "trackIds": list(reversed(track_ids))})
    assert [track["id"] for track in edited["tracks"]] == list(reversed(track_ids))

    preview = prepare(facade, edited["reviewId"], request="¿Cómo queda ahora?")
    assert preview["firstTurn"] is False
    answer = call(facade, "ai.run", {"previewId": preview["previewId"], "confirmed": True})["result"]
    assert answer["listChanged"] is True
    before, after = (body["messages"][0]["content"] for body in transport.bodies)
    assert before != after
    assert f"1. {details['tracks'][-1]['title']}" in after
    assert len(answer["conversation"]) == 4


@pytest.mark.parametrize(
    "failure,code",
    [
        ("empty_reply", "invalid_ai_response"),
        ("oversized_reply", "invalid_ai_response"),
        ("denied", "confirmation_required"),
        ("transport", "ai_request_failed"),
        ("cancelled", None),
    ],
)
def test_a_failed_turn_appends_nothing_to_the_conversation(chat_setup, failure, code):
    facade, transport, backend, _, _ = chat_setup
    review = current_review_id(backend)
    if failure == "empty_reply":
        transport.reply = ""
    elif failure == "oversized_reply":
        transport.reply = "x" * 4001
    elif failure == "transport":

        def fail():
            raise RuntimeError("synthetic provider failure")

        transport.on_send = fail
    token = ScanCancellationToken()
    preview = prepare(facade, review)
    params = {"previewId": preview["previewId"], "confirmed": failure != "denied"}
    if failure == "cancelled":
        token.cancel()
        assert call(facade, "ai.run", params, token=token) == {"cancelled": True, "result": None}
    else:
        with pytest.raises(BackendError) as error:
            call(facade, "ai.run", params)
        assert error.value.code == code
    assert history(facade) == {"conversation": [], "actions": []}
    assert prepare(facade, review)["firstTurn"] is True


def test_chat_history_and_reset_are_exact_and_read_only(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    turn(facade, current_review_id(backend))
    assert history(facade) == {
        "conversation": [{"role": "user", "text": QUESTION}, {"role": "assistant", "text": REPLY}],
        "actions": [],
    }
    assert call(facade, "ai.chat.reset") == {"conversation": []}
    assert history(facade) == {"conversation": [], "actions": []}
    assert len(transport.bodies) == 1
    for method, params in [
        ("ai.chat.history", {"conversation": []}),
        ("ai.chat.reset", {"reviewId": "x"}),
    ]:
        with pytest.raises(BackendError) as error:
            call(facade, method, params)
        assert error.value.code == "invalid_params"


def test_the_conversation_keeps_forty_messages_and_sends_the_last_twenty(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    review = current_review_id(backend)
    for index in range(22):
        turn(facade, review, request=f"Pregunta {index}")
    conversation = history(facade)["conversation"]
    assert len(conversation) == 40
    assert conversation[0] == {"role": "user", "text": "Pregunta 2"}
    assert conversation[1] == {"role": "assistant", "text": REPLY}
    assert conversation[-1] == {"role": "assistant", "text": REPLY}
    assert len(transport.bodies[-1]["messages"]) == 22


@pytest.mark.parametrize("discard", ["generation", "variant", "scan", "saved", "editor"])
def test_anything_that_discards_the_review_clears_the_conversation(chat_setup, discard):
    facade, _, backend, _, root = chat_setup
    turn(facade, current_review_id(backend))
    assert history(facade)["conversation"]
    playlist_id = backend.playlists.list_summaries()[0].id
    if discard == "generation":
        backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Otro set"})
    elif discard == "variant":
        assert backend.plan_id is not None
        backend.execute("prep.select", {"planId": backend.plan_id, "variant": "safe"})
    elif discard == "scan":
        backend.execute("library.scan", {"root": str(root)})
    elif discard == "saved":
        backend.execute("playlist.open", {"playlistId": playlist_id})
    else:
        backend.execute("playlist.edit.open", {"playlistId": playlist_id})
    assert history(facade) == {"conversation": [], "actions": []}


def test_a_change_of_the_ai_settings_clears_the_conversation_and_asks_consent_again(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    review = current_review_id(backend)
    turn(facade, review)
    assert history(facade)["conversation"]
    status = call(facade, "ai.status")
    updated = call(
        facade, "ai.settings.update", {"revision": status["revision"], "enabled": True, "autoAuthorize": True}
    )
    assert updated["autoAuthorize"] is True and updated["revision"] != status["revision"]
    assert history(facade) == {"conversation": [], "actions": []}
    assert prepare(facade, review)["firstTurn"] is True
    assert len(transport.bodies) == 1


def test_a_change_of_the_ai_credential_clears_the_conversation_and_asks_consent_again(chat_setup):
    facade, transport, backend, _, root = chat_setup
    review = current_review_id(backend)
    turn(facade, review)
    assert history(facade)["conversation"]
    other = root.resolve().parent / "dummy-other.env"
    other.write_bytes(b"NAN_API_KEY=synthetic-test-only\n")
    other.chmod(0o600)
    status = call(facade, "ai.status")
    selected = call(facade, "ai.credential.set", {"revision": status["revision"], "path": str(other)})
    assert selected["revision"] != status["revision"] and selected["configured"] is True
    assert history(facade) == {"conversation": [], "actions": []}
    assert prepare(facade, review)["firstTurn"] is True
    assert len(transport.bodies) == 1


def test_the_conversation_is_never_written_to_disk_and_a_restart_forgets_it(chat_setup):
    from xfinaudio.headless.backend import HeadlessBackend
    from xfinaudio.headless.optional_ai import OptionalAI

    facade, _, backend, _, _ = chat_setup
    turn(facade, current_review_id(backend))
    restarted = HeadlessBackend(backend.data_dir)
    assert call(OptionalAI(restarted, transport=ChatTransport()), "ai.chat.history") == {
        "conversation": [],
        "actions": [],
    }
    for path in backend.data_dir.rglob("*"):
        if path.is_file():
            assert QUESTION.encode() not in path.read_bytes()


def test_chat_refuses_a_list_over_one_hundred_tracks(chat_setup):
    from dataclasses import replace

    facade, transport, backend, _, _ = chat_setup
    assert backend.review is not None
    tracks = list(backend.review.recommendation.ordered_tracks)
    long_list = [tracks[index % len(tracks)] for index in range(101)]
    backend.review = replace(
        backend.review,
        recommendation=backend.review.recommendation.model_copy(update={"ordered_tracks": long_list}),
    )
    with pytest.raises(BackendError) as error:
        prepare(facade, current_review_id(backend))
    assert error.value.code == "invalid_params"
    assert transport.bodies == []


def test_payload_inspection_shows_the_exact_chat_messages_without_a_request(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    review = current_review_id(backend)
    turn(facade, review)
    preview = prepare(facade, review, request="¿Y después?")
    inspected = call(facade, "ai.payload", {"previewId": preview["previewId"]})
    assert transport.bodies and len(transport.bodies) == 1
    assert inspected["surface"] == "chat" and inspected["truncated"] is False
    sent = json.loads(inspected["body"])["messages"]
    assert [message["role"] for message in sent] == ["system", "user", "assistant", "user"]
    call(facade, "ai.run", {"previewId": preview["previewId"], "confirmed": True})
    assert transport.bodies[-1]["messages"] == sent


def test_the_review_commentary_surface_keeps_its_previous_shape(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = "Comentario sintético sobre el set."
    preview = call(
        facade, "ai.prepare", {"surface": "review", "request": "", "context": {"reviewId": current_review_id(backend)}}
    )
    assert "firstTurn" not in preview
    result = call(facade, "ai.run", {"previewId": preview["previewId"], "confirmed": True})["result"]
    assert set(result) == {"resultId", "surface", "kind", "title", "text", "proposal", "canApply"}
    assert result["surface"] == "review" and result["kind"] == "commentary" and result["canApply"] is False
    assert [message["role"] for message in transport.bodies[0]["messages"]] == ["system", "user"]
    assert call(facade, "ai.chat.history") == {"conversation": [], "actions": []}
