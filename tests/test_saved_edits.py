"""Every review command and the list assistant work on an opened saved playlist (S3).

A saved playlist opened as the list in progress is edited exactly like a generated
one: the same commands, the same undo history, and the same assistant applying a
proposal through ``ai.chat.apply``. The first and the last track are not protected,
and the assistant is never offered another variant of a saved list.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.test_headless_ai_context import setup as setup  # noqa: F401
from tests.test_headless_chat_actions import answer, chat_setup, remove, use_variant  # noqa: F401
from tests.test_headless_list_chat import QUESTION, call, turn
from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.library.models import TrackRecord


def saved_open(
    tmp_path: Path, count: int = 8, listed: int = 4, year_of: Any = None
) -> tuple[HeadlessBackend, list[TrackRecord], int, dict, list[str]]:
    """Open a saved playlist that leaves part of the library outside the list.

    The saved order is the reverse of the library order, so any edit that keeps the
    saved order is distinguishable from one that fell back to the scan order.
    """
    backend, records = seeded(tmp_path, count)
    if year_of is not None:
        backend.repository.save_scan_results(
            [record.model_copy(update={"release_year": year_of(index)}) for index, record in enumerate(records)]
        )
        records = backend._records()
    order = [record.path for record in records[:listed]][::-1]
    playlist = backend.playlists.create("Saved set", order)
    assert playlist.id is not None
    review = backend.execute("playlist.open", {"playlistId": playlist.id})
    assert review["editable"] is True
    assert review["variant"] == "saved"
    return backend, records, playlist.id, review, order


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def test_compare_and_replace_apply_to_the_saved_list(tmp_path: Path) -> None:
    backend, _, playlist_id, review, _ = saved_open(tmp_path)
    target = review["tracks"][1]["id"]
    comparison = backend.execute("review.compare", {"reviewId": review["reviewId"], "trackId": target})
    assert comparison["reviewId"] == review["reviewId"]
    assert comparison["available"] is True
    replacement = comparison["replacement"]
    assert replacement["id"] not in ids(review)
    applied = backend.execute(
        "review.replace",
        {"reviewId": review["reviewId"], "trackId": target, "replacementId": replacement["id"]},
    )
    assert applied["reviewId"] != review["reviewId"]
    assert (applied["variant"], applied["savedPlaylistId"]) == ("saved", playlist_id)
    assert ids(applied)[1] == replacement["id"]
    assert target not in ids(applied)
    assert (applied["canUndo"], applied["canRedo"]) == (True, False)


def test_remove_and_drop_edit_the_saved_list(tmp_path: Path) -> None:
    backend, _, _, review, _ = saved_open(tmp_path)
    target = review["tracks"][1]["id"]
    removed = backend.execute("review.remove", {"reviewId": review["reviewId"], "trackId": target})
    assert target not in ids(removed)
    dropped_target = removed["tracks"][1]["id"]
    dropped = backend.execute("review.drop", {"reviewId": removed["reviewId"], "trackId": dropped_target})
    assert dropped_target not in ids(dropped)
    assert len(dropped["tracks"]) == len(removed["tracks"]) - 1
    assert dropped["canUndo"] is True


def test_reorder_moves_the_first_and_the_last_track_of_the_saved_list(tmp_path: Path) -> None:
    backend, _, _, review, order = saved_open(tmp_path)
    original = ids(review)
    reordered = backend.execute("review.reorder", {"reviewId": review["reviewId"], "trackIds": original[::-1]})
    assert ids(reordered) == original[::-1]
    assert reordered["canUndo"] is True
    # The saved first and last tracks are ordinary tracks: nothing protects their ends.
    assert reordered["protectedTrackIds"] == []
    assert [track.path for track in backend.review.recommendation.ordered_tracks] == order[::-1]


def test_extend_grows_the_saved_list(tmp_path: Path) -> None:
    backend, _, _, review, _ = saved_open(tmp_path)
    grown = backend.execute("review.extend", {"reviewId": review["reviewId"], "targetTrackCount": 6})
    assert len(grown["tracks"]) == 6
    assert grown["extended"] == {"requested": 2, "added": 2, "outsideGenre": 0}
    assert set(ids(grown)) > set(ids(review))


def test_insert_adds_a_library_track_at_the_chosen_position(tmp_path: Path) -> None:
    backend, records, _, review, _ = saved_open(tmp_path)
    entering = next(record for record in records if identity(record) not in ids(review))
    inserted = backend.execute(
        "review.insert", {"reviewId": review["reviewId"], "trackId": identity(entering), "position": 1}
    )
    assert ids(inserted)[0] == identity(entering)
    assert len(inserted["tracks"]) == len(review["tracks"]) + 1


def test_swap_replaces_a_listed_track_with_a_chosen_library_track(tmp_path: Path) -> None:
    backend, records, _, review, _ = saved_open(tmp_path)
    target = review["tracks"][2]["id"]
    entering = next(record for record in records if identity(record) not in ids(review))
    swapped = backend.execute(
        "review.swap",
        {"reviewId": review["reviewId"], "trackId": target, "replacementTrackId": identity(entering)},
    )
    assert ids(swapped)[2] == identity(entering)
    assert target not in ids(swapped)
    assert len(swapped["tracks"]) == len(review["tracks"])


def test_fit_period_replaces_the_saved_tracks_outside_the_period(tmp_path: Path) -> None:
    backend, _, _, review, _ = saved_open(tmp_path, year_of=lambda index: 2000 if index < 4 else 1985)
    fitted = backend.execute("review.fit_period", {"reviewId": review["reviewId"], "yearMin": 1980, "yearMax": 1989})
    assert (fitted["period"]["yearMin"], fitted["period"]["yearMax"]) == (1980, 1989)
    assert fitted["period"]["replaced"] == 4
    assert fitted["period"]["kept"] == []
    assert [track.release_year for track in backend.review.recommendation.ordered_tracks] == [1985] * 4


def test_undo_and_redo_work_on_the_saved_list(tmp_path: Path) -> None:
    backend, _, _, review, _ = saved_open(tmp_path)
    with pytest.raises(Exception) as error:
        backend.execute("review.undo", {"reviewId": review["reviewId"]})
    assert getattr(error.value, "code", None) == "nothing_to_undo"
    original = ids(review)
    reordered = backend.execute("review.reorder", {"reviewId": review["reviewId"], "trackIds": original[::-1]})
    undone = backend.execute("review.undo", {"reviewId": reordered["reviewId"]})
    assert ids(undone) == original
    assert (undone["canUndo"], undone["canRedo"]) == (False, True)
    redone = backend.execute("review.redo", {"reviewId": undone["reviewId"]})
    assert ids(redone) == original[::-1]
    assert redone["reviewId"] not in {review["reviewId"], reordered["reviewId"], undone["reviewId"]}


def _saved_in_progress(backend: HeadlessBackend, selectors: dict) -> dict:
    """Replace the generated list in progress with the playlist the fixture saved."""
    opened = backend.execute("playlist.open", {"playlistId": int(selectors["saved"]["playlistIds"][0])})
    assert opened["editable"] is True
    assert backend.review_id == opened["reviewId"]
    return opened


def test_a_chat_turn_applies_a_proposed_remove_on_the_saved_list(chat_setup: Any) -> None:  # noqa: F811
    facade, transport, backend, selectors, _ = chat_setup
    opened = _saved_in_progress(backend, selectors)
    current = ids(opened)
    transport.reply = answer(remove(2))
    result = turn(facade, backend.review_id)["result"]
    assert [action["type"] for action in result["actions"]] == ["remove"]
    sent = transport.bodies[0]["messages"]
    assert sent[-1]["content"] == QUESTION
    # A saved list has no other variant to switch to, and it is not short of anything.
    assert "- otras alternativas: ninguna" in sent[0]["content"]
    assert "- variante actual: saved" in sent[0]["content"]
    applied = call(facade, "ai.chat.apply", {"actionId": result["actions"][0]["actionId"]})
    assert applied["review"]["variant"] == "saved"
    assert current[1] not in ids(applied["review"])
    assert (applied["review"]["canUndo"], applied["review"]["canRedo"]) == (True, False)
    assert applied["actions"] == []


@pytest.mark.parametrize("variant", ["adventurous", "saved"])
def test_a_use_variant_proposed_for_the_saved_list_is_dropped(chat_setup: Any, variant: str) -> None:  # noqa: F811
    facade, transport, backend, selectors, _ = chat_setup
    _saved_in_progress(backend, selectors)
    transport.reply = answer(use_variant(variant), remove(2))
    result = turn(facade, backend.review_id)["result"]
    assert [action["type"] for action in result["actions"]] == ["remove"]
    assert result["droppedActions"] == 1
