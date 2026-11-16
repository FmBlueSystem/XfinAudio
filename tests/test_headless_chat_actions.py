"""The assistant proposes list changes and the DJ applies one with a single click.

Every turn runs through the injected transport: the provider is never called, and
applying a change never sends anything at all.
"""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from tests.test_headless_ai_context import setup as setup  # noqa: F401
from tests.test_headless_list_chat import QUESTION, call, history, prepare, turn
from tests.test_headless_list_chat import chat_setup as _chat_setup
from xfinaudio.headless import generated_review as generated_review_module
from xfinaudio.headless.common import BackendError, _public_track

# The list-conversation fixture and helpers are reused rather than copied, so these tests
# run exactly the same disclosed chat turn as the conversation tests do.
chat_setup = _chat_setup


def answer(*actions: dict, reply: str = "Propongo dos cambios.") -> str:
    return json.dumps({"reply": reply, "actions": list(actions)})


def replace_at(position: int, reason: str = "Baja energía") -> dict:
    return {"type": "replace", "position": position, "reason": reason}


def move(position: int, to: int, reason: str = "Sube antes") -> dict:
    return {"type": "move", "position": position, "to": to, "reason": reason}


def extend(to: int, reason: str = "La lista quedó corta") -> dict:
    return {"type": "extend", "to": to, "reason": reason}


def use_variant(variant: str = "adventurous", reason: str = "Más pistas") -> dict:
    return {"type": "use_variant", "variant": variant, "reason": reason}


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def tracks(backend) -> list[dict]:
    assert backend.review_id is not None
    return backend.execute("review.details", {"reviewId": backend.review_id})["tracks"]


def test_a_chat_turn_publishes_its_proposed_changes_without_paths_or_track_ids(chat_setup):
    facade, transport, backend, _, root = chat_setup
    transport.reply = answer(replace_at(3), move(4, 1), replace_at(1, "x" * 201))
    result = turn(facade, backend.review_id)["result"]
    assert result["text"] == "Propongo dos cambios."
    assert result["droppedActions"] == 1
    current = tracks(backend)
    replacement_action, move_action = result["actions"]
    assert set(replacement_action) == {"actionId", "type", "position", "title", "artist", "reason", "replacement"}
    assert set(move_action) == {"actionId", "type", "position", "title", "artist", "reason", "to"}
    assert replacement_action["type"] == "replace" and replacement_action["position"] == 3
    assert replacement_action["title"] == current[2]["title"]
    assert replacement_action["artist"] == current[2]["artist"]
    assert replacement_action["reason"] == "Baja energía"
    assert set(replacement_action["replacement"]) == {"title", "artist", "bpm", "key"}
    comparison = backend.execute("review.compare", {"reviewId": backend.review_id, "trackId": current[2]["id"]})
    assert replacement_action["replacement"] == {
        key: comparison["replacement"][key] for key in ("title", "artist", "bpm", "key")
    }
    assert move_action["position"] == 4 and move_action["to"] == 1
    assert move_action["title"] == current[3]["title"]
    assert result["conversation"] == [
        {"role": "user", "text": QUESTION},
        {"role": "assistant", "text": "Propongo dos cambios."},
    ]
    published = json.dumps(result)
    assert str(root) not in published and ".flac" not in published
    for track in current:
        assert track["id"] not in published


def test_a_replace_without_an_engine_replacement_is_dropped_and_counted(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    monkeypatch.setattr(
        generated_review_module,
        "recommendation_with_replacement",
        lambda recommendation, *args, **kwargs: recommendation,
    )
    transport.reply = answer(replace_at(2), move(1, 3))
    result = turn(facade, backend.review_id)["result"]
    assert result["droppedActions"] == 1
    assert [action["type"] for action in result["actions"]] == ["move"]


def test_history_reports_the_pending_changes_and_never_sends_anything(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2))
    result = turn(facade, backend.review_id)["result"]
    assert history(facade) == {"conversation": result["conversation"], "actions": result["actions"]}
    assert len(transport.bodies) == 1


def test_the_next_successful_turn_replaces_the_pending_changes(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2))
    first = turn(facade, backend.review_id)["result"]["actions"]
    transport.reply = answer(move(3, 1))
    second = turn(facade, backend.review_id, request="¿Y una más?")["result"]["actions"]
    assert [action["actionId"] for action in second] != [action["actionId"] for action in first]
    assert history(facade)["actions"] == second


@pytest.mark.parametrize("cleared_by", ["reset", "review", "saved"])
def test_clearing_the_conversation_clears_the_pending_changes(chat_setup, cleared_by):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2), move(1, 3))
    turn(facade, backend.review_id)
    assert history(facade)["actions"]
    if cleared_by == "reset":
        assert call(facade, "ai.chat.reset") == {"conversation": []}
    elif cleared_by == "review":
        backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Otro set"})
    else:
        backend.execute("playlist.open", {"playlistId": backend.playlists.list_summaries()[0].id})
    assert history(facade) == {"conversation": [], "actions": []}


def test_applying_a_replace_uses_the_review_replace_edit_and_is_undoable(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(3))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    previous = backend.review_id
    original = ids(backend.execute("review.details", {"reviewId": previous}))
    sent = len(transport.bodies)
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert set(applied) == {"review", "actions"}
    review = applied["review"]
    assert set(review) == set(backend.execute("review.details", {"reviewId": review["reviewId"]}))
    assert review["reviewId"] != previous
    assert backend.review_id == review["reviewId"]
    assert review["canUndo"] is True and review["canRedo"] is False
    assert applied["actions"] == []
    replaced = ids(review)
    assert len(replaced) == len(original)
    assert replaced[2] not in original and original[2] not in replaced
    assert replaced[:2] == original[:2] and replaced[3:] == original[3:]
    assert len(transport.bodies) == sent
    undone = backend.execute("review.undo", {"reviewId": review["reviewId"]})
    assert ids(undone) == original


def test_applying_a_move_uses_the_review_reorder_edit_and_is_undoable(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(move(1, 3))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert ids(applied["review"]) == [original[1], original[2], original[0], *original[3:]]
    assert applied["actions"] == []
    undone = backend.execute("review.undo", {"reviewId": applied["review"]["reviewId"]})
    assert ids(undone) == original


def test_a_move_position_is_applied_as_written_and_the_rest_are_redrawn(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(move(1, 4), move(4, 1))
    first, second = turn(facade, backend.review_id)["result"]["actions"]
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    applied = call(facade, "ai.chat.apply", {"actionId": second["actionId"]})
    assert ids(applied["review"]) == [original[3], original[0], original[1], original[2]]
    pending = applied["actions"]
    assert [item["actionId"] for item in pending] == [first["actionId"]]
    assert pending[0]["position"] == 2 and pending[0]["to"] == 4
    final = call(facade, "ai.chat.apply", {"actionId": pending[0]["actionId"]})
    assert ids(final["review"]) == [original[3], original[1], original[2], original[0]]


def test_a_replace_position_is_redrawn_after_another_change_was_applied(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(move(1, 4), replace_at(2))
    moved, replaced = turn(facade, backend.review_id)["result"]["actions"]
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    applied = call(facade, "ai.chat.apply", {"actionId": moved["actionId"]})
    assert ids(applied["review"]) == [original[1], original[2], original[3], original[0]]
    pending = applied["actions"]
    assert [item["actionId"] for item in pending] == [replaced["actionId"]]
    assert pending[0]["position"] == 1
    assert pending[0]["replacement"] == replaced["replacement"]


def test_an_unknown_or_already_applied_action_fails_with_stale_ai_and_changes_nothing(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(3))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    for action_id in (str(uuid4()),):
        with pytest.raises(BackendError) as error:
            call(facade, "ai.chat.apply", {"actionId": action_id})
        assert error.value.code == "stale_ai"
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    after = backend.review_id
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert error.value.code == "stale_ai"
    assert backend.review_id == after == applied["review"]["reviewId"]
    assert history(facade)["actions"] == []


def test_a_track_that_left_the_list_cannot_be_applied(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(move(3, 1))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    # A manual edit removes the track the pending change names; the conversation stays.
    target = tracks(backend)[2]["id"]
    comparison = backend.execute("review.compare", {"reviewId": backend.review_id, "trackId": target})
    manual = backend.execute(
        "review.replace",
        {
            "reviewId": backend.review_id,
            "trackId": target,
            "replacementId": comparison["replacement"]["id"],
        },
    )
    assert target not in ids(manual)
    assert len(history(facade)["actions"]) == 0
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert error.value.code == "stale_ai"
    assert ids(backend.execute("review.details", {"reviewId": backend.review_id})) == ids(manual)


def test_a_track_that_became_protected_cannot_be_applied(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    review = backend.review
    assert review is not None
    ordered = list(review.recommendation.ordered_tracks)
    backend.review = replace(
        review,
        recommendation=review.recommendation.model_copy(
            update={"applied_controls": {**review.recommendation.applied_controls, "start_path": ordered[1].path}}
        ),
    )
    before = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert error.value.code == "stale_ai"
    assert ids(backend.execute("review.details", {"reviewId": backend.review_id})) == before


def test_a_replacement_the_engine_no_longer_offers_cannot_be_applied(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    before = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    monkeypatch.setattr(
        generated_review_module,
        "recommendation_with_replacement",
        lambda recommendation, *args, **kwargs: recommendation,
    )
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert error.value.code == "stale_ai"
    assert ids(backend.execute("review.details", {"reviewId": backend.review_id})) == before


def test_an_extend_turn_publishes_its_target_and_applying_it_grows_the_list(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(extend(6))
    previous = backend.review_id
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    assert set(action) == {"actionId", "type", "to", "reason"}
    assert action["type"] == "extend" and action["to"] == 6
    assert action["reason"] == "La lista quedó corta"
    original = ids(backend.execute("review.details", {"reviewId": previous}))
    sent = len(transport.bodies)
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert set(applied) == {"review", "actions", "extended"}
    assert applied["extended"] == {"requested": 2, "added": 2, "outsideGenre": 0}
    review = applied["review"]
    assert set(review) == set(backend.execute("review.details", {"reviewId": review["reviewId"]}))
    assert review["reviewId"] != previous and (review["canUndo"], review["canRedo"]) == (True, False)
    grown = ids(review)
    assert len(grown) == 6 and set(original) <= set(grown)
    assert applied["actions"] == []
    assert len(transport.bodies) == sent
    assert ids(backend.execute("review.undo", {"reviewId": review["reviewId"]})) == original


def test_an_extend_with_no_candidates_is_passed_through_and_the_action_stays_pending(chat_setup, monkeypatch):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(extend(6))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    before = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    monkeypatch.setattr(
        generated_review_module,
        "recommendation_extended",
        lambda recommendation, *args, **kwargs: (recommendation, 0),
    )
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert error.value.code == "no_candidates"
    assert ids(backend.execute("review.details", {"reviewId": backend.review_id})) == before
    assert [item["actionId"] for item in history(facade)["actions"]] == [action["actionId"]]


def test_a_use_variant_turn_publishes_the_variant_and_its_count_and_is_never_applied(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(use_variant())
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    assert set(action) == {"actionId", "type", "variant", "trackCount", "reason"}
    assert action["type"] == "use_variant" and action["variant"] == "adventurous"
    assert backend.plan is not None
    offered = next(item for item in backend.plan.variants if item.name == "adventurous")
    assert action["trackCount"] == len(offered.recommendation.ordered_tracks)
    before = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert error.value.code == "stale_ai"
    assert ids(backend.execute("review.details", {"reviewId": backend.review_id})) == before
    assert [item["actionId"] for item in history(facade)["actions"]] == [action["actionId"]]


def test_a_use_variant_naming_the_current_variant_is_dropped_and_counted(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    assert backend.review is not None
    current = backend.review.variant_name
    transport.reply = answer(use_variant(current), extend(6))
    result = turn(facade, backend.review_id)["result"]
    assert result["droppedActions"] == 1
    assert [action["type"] for action in result["actions"]] == ["extend"]


def test_apply_takes_exactly_one_action_id(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    for params in ({}, {"actionId": action["actionId"], "reviewId": backend.review_id}, {"actionId": 7}):
        with pytest.raises(BackendError) as error:
            call(facade, "ai.chat.apply", params)
        assert error.value.code == "invalid_params"
    assert backend.review_id is not None
    assert len(history(facade)["actions"]) == 1
    assert len(transport.bodies) == 1


def test_a_chat_turn_without_actions_publishes_an_empty_list(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = "Solo un comentario."
    result = turn(facade, backend.review_id)["result"]
    assert result["actions"] == [] and result["droppedActions"] == 0
    assert history(facade)["actions"] == []


def test_a_prepared_turn_still_runs_through_the_injected_transport(chat_setup):
    """The structured request is the only change: the prepared body is still inspectable."""
    facade, transport, backend, _, _ = chat_setup
    preview = prepare(facade, backend.review_id)
    inspected = call(facade, "ai.payload", {"previewId": preview["previewId"]})
    system = json.loads(inspected["body"])["messages"][0]["content"]
    assert "JSON" in system and "N = 4" in system
    assert "Resumen de la generación" in system
    assert transport.bodies == []


def remove(position: int, reason: str = "Sobra") -> dict:
    return {"type": "remove", "position": position, "reason": reason}


def add(ref: str = "L1", position: int = 5, reason: str = "Encaja al final") -> dict:
    return {"type": "add", "ref": ref, "position": position, "reason": reason}


def replace_with(position: int, ref: str = "L1", reason: str = "Mejor encaje") -> dict:
    return {"type": "replace_with", "position": position, "ref": ref, "reason": reason}


def reorder(*order: int, reason: str = "Sube la última") -> dict:
    return {"type": "reorder", "order": list(order), "reason": reason}


def undo(reason: str = "Mejor no cambiar nada") -> dict:
    return {"type": "undo", "reason": reason}


def searched(facade, transport, backend, *searches: dict) -> None:
    """One successful turn that asks for a library search and receives its results."""
    transport.replies = [
        json.dumps(
            {"reply": "Busco en la biblioteca.", "actions": [], "searches": list(searches) or [{"query": "test"}]}
        ),
        json.dumps({"reply": "Estas son las pistas que encontré.", "actions": []}),
    ]
    turn(facade, backend.review_id)


def library_track(backend, title: str) -> dict:
    record = next(record for record in backend._records(checked=frozenset()) if record.title == title)
    return _public_track(record)


def test_a_remove_action_drops_the_track_without_a_replacement_and_is_undoable(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(remove(3))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    current = tracks(backend)
    assert set(action) == {"actionId", "type", "position", "title", "artist", "reason"}
    assert action["type"] == "remove" and action["position"] == 3
    assert action["title"] == current[2]["title"] and action["artist"] == current[2]["artist"]
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    sent = len(transport.bodies)
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert ids(applied["review"]) == [original[0], original[1], original[3]]
    assert applied["actions"] == []
    assert len(transport.bodies) == sent
    assert ids(backend.execute("review.undo", {"reviewId": applied["review"]["reviewId"]})) == original


def test_an_add_action_publishes_the_found_track_and_inserts_it_at_its_position(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    searched(facade, transport, backend)
    transport.reply = answer(add(ref="L2", position=2))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    assert set(action) == {"actionId", "type", "position", "track", "reason"}
    assert action["type"] == "add" and action["position"] == 2 and action["reason"] == "Encaja al final"
    assert set(action["track"]) == {"title", "artist", "bpm", "key"}
    found = library_track(backend, "Electron test 6")
    assert action["track"] == {key: found[key] for key in ("title", "artist", "bpm", "key")}
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert ids(applied["review"]) == [original[0], found["id"], original[1], original[2], original[3]]
    assert applied["actions"] == []
    assert ids(backend.execute("review.undo", {"reviewId": applied["review"]["reviewId"]})) == original


def test_a_replace_with_action_swaps_the_track_at_its_position(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    searched(facade, transport, backend)
    transport.reply = answer(replace_with(2, ref="L1"))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    current = tracks(backend)
    assert set(action) == {"actionId", "type", "position", "title", "artist", "track", "reason"}
    assert action["position"] == 2 and action["title"] == current[1]["title"]
    found = library_track(backend, "Electron test 5")
    assert action["track"] == {key: found[key] for key in ("title", "artist", "bpm", "key")}
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert ids(applied["review"]) == [original[0], found["id"], original[2], original[3]]
    assert ids(backend.execute("review.undo", {"reviewId": applied["review"]["reviewId"]})) == original


def test_a_reorder_action_publishes_how_many_tracks_move_and_reorders_the_list(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(reorder(4, 1, 2, 3))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    assert set(action) == {"actionId", "type", "moved", "reason"}
    assert action["type"] == "reorder" and action["moved"] == 4
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    applied = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert ids(applied["review"]) == [original[3], original[0], original[1], original[2]]
    assert ids(backend.execute("review.undo", {"reviewId": applied["review"]["reviewId"]})) == original


def test_an_undo_action_undoes_the_previous_review_edit(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(move(1, 3))
    moved = turn(facade, backend.review_id)["result"]["actions"][0]
    original = ids(backend.execute("review.details", {"reviewId": backend.review_id}))
    applied = call(facade, "ai.chat.apply", {"actionId": moved["actionId"]})
    assert ids(applied["review"]) != original
    transport.reply = answer(undo())
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    assert set(action) == {"actionId", "type", "reason"}
    undone = call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    assert ids(undone["review"]) == original


def test_an_undo_with_nothing_to_undo_is_dropped_and_counted(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(undo())
    result = turn(facade, backend.review_id)["result"]
    assert result["actions"] == [] and result["droppedActions"] == 1
    assert history(facade)["actions"] == []


def test_an_undo_with_another_change_keeps_only_the_undo(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(move(1, 3))
    moved = turn(facade, backend.review_id)["result"]["actions"][0]
    call(facade, "ai.chat.apply", {"actionId": moved["actionId"]})
    transport.reply = answer(undo(), reorder(4, 1, 2, 3), remove(2))
    result = turn(facade, backend.review_id)["result"]
    assert [action["type"] for action in result["actions"]] == ["undo"]
    assert result["droppedActions"] == 2


def test_a_reference_never_issued_is_dropped_and_counted(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(add(ref="L1", position=5), replace_with(2, ref="L4"))
    result = turn(facade, backend.review_id)["result"]
    assert result["actions"] == [] and result["droppedActions"] == 2


def test_a_reference_from_a_previous_conversation_is_dropped(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    searched(facade, transport, backend)
    assert call(facade, "ai.chat.reset") == {"conversation": []}
    searched(facade, transport, backend, {"query": "test 5"})
    transport.reply = answer(add(ref="L3", position=5))
    result = turn(facade, backend.review_id)["result"]
    assert result["actions"] == [] and result["droppedActions"] == 1


def test_a_path_or_a_track_id_in_place_of_a_reference_is_dropped_and_counted(chat_setup):
    facade, transport, backend, _, root = chat_setup
    track_id = tracks(backend)[0]["id"]
    path = str(root / "track-5.flac")
    transport.reply = answer(add(ref=path, position=5), add(ref=track_id, position=5))
    result = turn(facade, backend.review_id)["result"]
    assert result["actions"] == [] and result["droppedActions"] == 2


def test_an_add_that_would_break_a_protected_opening_is_dropped_and_counted(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    searched(facade, transport, backend)
    review = backend.review
    assert review is not None
    ordered = list(review.recommendation.ordered_tracks)
    backend.review = replace(
        review,
        recommendation=review.recommendation.model_copy(
            update={"applied_controls": {**review.recommendation.applied_controls, "start_path": ordered[0].path}}
        ),
    )
    transport.reply = answer(add(ref="L1", position=1), add(ref="L1", position=2))
    result = turn(facade, backend.review_id)["result"]
    assert [action["position"] for action in result["actions"]] == [2]
    assert result["droppedActions"] == 1


def test_a_bad_permutation_is_dropped_and_counted(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(reorder(1, 2, 2, 3))
    result = turn(facade, backend.review_id)["result"]
    assert result["actions"] == [] and result["droppedActions"] == 1
    assert ids(backend.execute("review.details", {"reviewId": backend.review_id}))


def test_a_reply_with_more_than_eight_changes_keeps_eight(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    backend.execute("prep.generate", {"targetTrackCount": 8, "name": "Ocho pistas"})
    assert backend.review is not None and len(tracks(backend)) == 8
    items = [remove(index) for index in range(1, 9)] + [extend(10)]
    transport.reply = answer(*items)
    result = turn(facade, backend.review_id)["result"]
    assert [action["type"] for action in result["actions"]] == ["remove"] * 8
    assert result["droppedActions"] == 1


def test_a_pending_reorder_cannot_apply_once_the_list_changed(chat_setup):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(reorder(2, 1, 3, 4), replace_at(3))
    kept = turn(facade, backend.review_id)["result"]["actions"]
    assert [action["type"] for action in kept] == ["reorder", "replace"]
    applied = call(facade, "ai.chat.apply", {"actionId": kept[1]["actionId"]})
    before = ids(applied["review"])
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": kept[0]["actionId"]})
    assert error.value.code == "stale_ai"
    assert ids(backend.execute("review.details", {"reviewId": backend.review_id})) == before
