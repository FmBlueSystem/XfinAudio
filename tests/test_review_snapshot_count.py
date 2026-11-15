"""One core command reads the library source snapshot once, plus one final check.

The snapshot is what makes every review edit honest about the library on disk, but
rebuilding it for each guard inside the same command re-reads the whole library
several times per operation. Every answer and every refusal stays identical: the
command builds the snapshot at the start and refreshes it once for the final check.
"""

from __future__ import annotations

import pytest

from tests.test_headless_ai_context import setup as setup  # noqa: F401
from tests.test_headless_chat_actions import answer, replace_at
from tests.test_headless_chat_actions import chat_setup as _chat_setup
from tests.test_headless_list_chat import call, prepare
from xfinaudio.headless import generated_review as generated_review_module

chat_setup = _chat_setup

# One build at the start of the command and one for the final check that guards
# against a change during the command.
MAX_SNAPSHOT_BUILDS = 2


@pytest.fixture
def snapshot_builds(monkeypatch):
    """Count how often the library source snapshot is actually rebuilt.

    A rebuilt snapshot is a new mapping; a reused one is the very mapping handed out
    before, so a command that shares it cannot hide behind the call count alone.
    """
    builds: list[int] = []
    previous: list[object] = [None]
    read = generated_review_module.GeneratedReview._sources

    def counting(self, *args, **kwargs):
        snapshot = read(self, *args, **kwargs)
        if snapshot is not previous[0]:
            builds.append(len(builds))
            previous[0] = snapshot
        return snapshot

    monkeypatch.setattr(generated_review_module.GeneratedReview, "_sources", counting)
    return builds


def ids(backend) -> list[str]:
    assert backend.review_id is not None
    return [track["id"] for track in backend.execute("review.details", {"reviewId": backend.review_id})["tracks"]]


def test_one_compare_builds_the_library_snapshot_at_most_twice(setup, snapshot_builds):
    backend, selectors, _ = setup
    review_id = selectors["review"]["reviewId"]
    target = backend.execute("review.details", {"reviewId": review_id})["tracks"][2]["id"]
    del snapshot_builds[:]
    comparison = backend.execute("review.compare", {"reviewId": review_id, "trackId": target})
    assert comparison["available"] is True
    assert comparison["replacement"] is not None
    assert len(snapshot_builds) <= MAX_SNAPSHOT_BUILDS


def test_one_replace_builds_the_library_snapshot_at_most_twice(setup, snapshot_builds):
    backend, selectors, _ = setup
    review_id = selectors["review"]["reviewId"]
    original = ids(backend)
    target = original[2]
    comparison = backend.execute("review.compare", {"reviewId": review_id, "trackId": target})
    replacement_id = comparison["replacement"]["id"]
    del snapshot_builds[:]
    replaced = backend.execute(
        "review.replace", {"reviewId": review_id, "trackId": target, "replacementId": replacement_id}
    )
    assert replaced["reviewId"] != review_id
    assert target not in [track["id"] for track in replaced["tracks"]]
    assert len(snapshot_builds) <= MAX_SNAPSHOT_BUILDS


def test_one_chat_turn_proposing_a_replace_builds_the_snapshot_at_most_twice(chat_setup, snapshot_builds):
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2))
    # A chat turn is two core commands in the app: prepare the disclosed context, then run it.
    del snapshot_builds[:]
    prepared = prepare(facade, backend.review_id)
    assert len(snapshot_builds) <= MAX_SNAPSHOT_BUILDS
    del snapshot_builds[:]
    result = call(facade, "ai.run", {"previewId": prepared["previewId"], "confirmed": True})["result"]
    assert [action["type"] for action in result["actions"]] == ["replace"]
    assert result["droppedActions"] == 0
    assert len(snapshot_builds) <= MAX_SNAPSHOT_BUILDS
