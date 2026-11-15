"""The opt-in chat diagnostic log: one JSON line per list-assistant event.

Nothing is written unless the core starts with ``XFINAUDIO_CHAT_LOG=1``, a log that
cannot be written never fails the turn it describes, and no line ever carries a file
path, a track identity, the credential or the system message. Every turn runs through
the injected transport: the provider is never called.
"""

from __future__ import annotations

import json
import stat

import pytest

from tests.test_headless_ai_context import setup as setup  # noqa: F401
from tests.test_headless_chat_actions import answer, move, replace_at, tracks
from tests.test_headless_list_chat import QUESTION, REPLY, call, prepare, turn
from tests.test_headless_list_chat import chat_setup as _chat_setup
from xfinaudio.headless.chat_log import MAX_CHAT_LOG_BYTES, ChatLog
from xfinaudio.headless.common import BackendError

chat_setup = _chat_setup


def enable(monkeypatch) -> None:
    monkeypatch.setenv("XFINAUDIO_CHAT_LOG", "1")


def log_path(backend):
    return backend.data_dir / "logs" / "list-chat.log"


def log_entries(backend) -> list[dict]:
    path = log_path(backend)
    assert path.exists()
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_without_the_variable_nothing_is_written_and_the_turn_is_unchanged(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2), {"type": "remove", "position": 1, "reason": "x"})
    result = turn(facade, backend.review_id)["result"]
    assert not (backend.data_dir / "logs").exists()
    assert "rawText" not in result and "droppedItems" not in result
    assert result["text"] == "Propongo dos cambios."
    assert result["droppedActions"] == 1


def test_a_turn_appends_one_line_with_the_reply_the_actions_and_each_dropped_value(chat_setup, monkeypatch):
    facade, transport, backend, _, root = chat_setup
    enable(monkeypatch)
    refused = {"type": "remove", "position": 1, "reason": "x"}
    transport.reply = answer(replace_at(3), move(4, 1), refused)
    result = turn(facade, backend.review_id)["result"]
    entries = log_entries(backend)
    assert [entry["event"] for entry in entries] == ["turn"]
    entry = entries[0]
    assert entry["message"] == QUESTION
    assert entry["rawText"] == transport.reply
    assert entry["reply"] == "Propongo dos cambios."
    assert entry["actions"] == result["actions"]
    assert entry["droppedActions"] == 1
    assert entry["droppedItems"] == [{"raw": refused, "reason": "unsupported change"}]
    assert entry["listChanged"] is False
    assert entry["trackCount"] == 4
    assert entry["time"].endswith("+00:00")
    text = log_path(backend).read_text(encoding="utf-8")
    assert str(root) not in text and ".flac" not in text
    assert str(root.resolve().parent / "dummy-selected.env") not in text
    for track_id in [track["id"] for track in tracks(backend)]:
        assert track_id not in text


def test_a_turn_without_changes_says_the_list_did_not_change(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    enable(monkeypatch)
    transport.reply = json.dumps({"reply": "Nada que cambiar.", "actions": []})
    turn(facade, backend.review_id)
    entry = log_entries(backend)[0]
    assert entry["actions"] == [] and entry["droppedActions"] == 0 and entry["droppedItems"] == []
    assert entry["reply"] == "Nada que cambiar."


def test_a_failed_turn_logs_the_question_and_the_error_code(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    enable(monkeypatch)
    transport.reply = "   "
    with pytest.raises(BackendError) as failure:
        turn(facade, backend.review_id)
    assert failure.value.code == "invalid_ai_response"
    entries = log_entries(backend)
    assert [entry["event"] for entry in entries] == ["turn_failed"]
    assert entries[0]["message"] == QUESTION
    assert entries[0]["errorCode"] == "invalid_ai_response"


def test_apply_and_reset_are_logged_with_the_new_order(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    enable(monkeypatch)
    transport.reply = answer(replace_at(3))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert call(facade, "ai.chat.reset") == {"conversation": []}
    entries = log_entries(backend)
    assert [entry["event"] for entry in entries] == ["turn", "apply", "reset"]
    assert entries[1]["action"] == action
    assert entries[1]["order"] == [
        {"position": index, "title": track["title"]} for index, track in enumerate(applied["review"]["tracks"], 1)
    ]
    assert set(entries[2]) == {"time", "event"}


def test_a_failed_apply_logs_the_action_identity_and_the_error_code(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    enable(monkeypatch)
    transport.reply = answer(replace_at(3))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    with pytest.raises(BackendError) as failure:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert failure.value.code == "stale_ai"
    entry = log_entries(backend)[-1]
    assert entry["event"] == "apply_failed"
    assert entry["actionId"] == action["actionId"]
    assert entry["errorCode"] == "stale_ai"


def test_the_log_file_is_private_and_rotates_when_it_passes_two_megabytes(tmp_path, monkeypatch):
    enable(monkeypatch)
    log = ChatLog(tmp_path / "data")
    log.write("turn", message="first")
    path = log.path
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    log.write("turn", message="x" * MAX_CHAT_LOG_BYTES)
    backup = path.with_name("list-chat.log.1")
    rotated = [json.loads(line) for line in backup.read_text(encoding="utf-8").splitlines()]
    assert [entry["message"] for entry in rotated] == ["first"]
    current = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(current) == 1 and current[0]["message"] == "x" * MAX_CHAT_LOG_BYTES


def test_a_log_that_cannot_be_written_never_fails_the_turn(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    enable(monkeypatch)
    (backend.data_dir / "logs").write_text("not a directory", encoding="utf-8")
    transport.reply = answer(replace_at(2))
    result = turn(facade, backend.review_id)["result"]
    assert result["text"] == "Propongo dos cambios."
    assert result["actions"][0]["position"] == 2


def test_history_never_writes_a_line(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    enable(monkeypatch)
    call(facade, "ai.chat.history")
    prepare(facade, backend.review_id)
    assert not (backend.data_dir / "logs").exists()
    turn(facade, backend.review_id)
    assert [entry["event"] for entry in log_entries(backend)] == ["turn"]
    assert REPLY in log_path(backend).read_text(encoding="utf-8")
