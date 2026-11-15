"""Review commands read the disk identity only of the tracks that take part (S2, S3).

Every answer and every refusal stays identical: a command reads the disk identity of the
tracks in its list and of each track about to enter it, and compares each one with the
identity generation recorded. Every other library track contributes its stored record
without touching the disk, so one compare on a large library costs tens of identity
reads instead of one per track.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_ai_context import setup as setup  # noqa: F401
from tests.test_headless_chat_actions import answer, replace_at, turn
from tests.test_headless_list_chat import call
from tests.test_headless_list_chat import chat_setup as _chat_setup
from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless import generated_review as generated_review_module
from xfinaudio.headless import profiles as profiles_module
from xfinaudio.headless.common import BackendError

chat_setup = _chat_setup

# S3: one compare on a 200-track library with a 10-track list reads at most this many.
MAX_COMPARE_IDENTITY_READS = 60
TRACKS_IN_LIBRARY = 200
TRACKS_IN_LIST = 10

MUTATIONS = ("changed", "moved", "deleted")


@pytest.fixture
def identity_reads(monkeypatch):
    """Count every on-disk identity read a review command makes, wherever it comes from."""
    reads: list[str] = []
    for module in (generated_review_module, profiles_module):
        read = module.source_identity

        def counting(path, _read=read):
            reads.append(str(path))
            return _read(path)

        monkeypatch.setattr(module, "source_identity", counting)
    return reads


def generated(tmp_path: Path, count: int = 8) -> tuple[object, list, dict]:
    backend, records = seeded(tmp_path, count)
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": 4})


def state(backend) -> tuple[object, ...]:
    """Everything a refused command must leave exactly as it found it."""
    return (
        backend.review,
        backend.review_id,
        list(backend.review_actions.history),
        list(backend.review_actions.future),
        dict(backend.review_actions.offers),
    )


def mutate(path: str, mutation: str) -> None:
    target = Path(path)
    if mutation == "changed":
        target.write_bytes(b"changed after generation")
    elif mutation == "moved":
        target.rename(target.with_name(target.name + ".moved"))
    else:
        target.unlink()


def test_one_compare_reads_the_disk_identity_only_of_the_tracks_that_take_part(tmp_path: Path, identity_reads) -> None:
    backend, _ = seeded(tmp_path, TRACKS_IN_LIBRARY)
    result = backend.execute("prep.generate", {"targetTrackCount": TRACKS_IN_LIST})
    assert len(result["tracks"]) == TRACKS_IN_LIST
    del identity_reads[:]
    comparison = backend.execute(
        "review.compare", {"reviewId": result["reviewId"], "trackId": result["tracks"][2]["id"]}
    )
    assert comparison["available"] is True
    assert comparison["replacement"] is not None
    # The list, the entering track, and no other track of the two hundred in the library.
    assert len(identity_reads) <= MAX_COMPARE_IDENTITY_READS


@pytest.mark.parametrize("mutation", MUTATIONS)
@pytest.mark.parametrize(
    "method",
    [
        "review.compare",
        "review.replace",
        "review.remove",
        "review.reorder",
        "review.extend",
        "review.undo",
        "review.redo",
    ],
)
def test_a_track_of_the_list_changed_on_disk_refuses_every_edit(tmp_path: Path, method: str, mutation: str) -> None:
    backend, _, result = generated(tmp_path)
    tracks = [track["id"] for track in result["tracks"]]
    offered = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": tracks[2]})["replacement"][
        "id"
    ]
    review_id = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": tracks[::-1]})[
        "reviewId"
    ]
    # An undo stack for the undo case and a redo stack for the redo case, on the same revision.
    review_id = backend.execute("review.undo", {"reviewId": review_id})["reviewId"]
    mutate(backend.review.recommendation.ordered_tracks[2].path, mutation)
    params = {
        "review.compare": {"trackId": tracks[2]},
        "review.replace": {"trackId": tracks[2], "replacementId": offered},
        "review.remove": {"trackId": tracks[1]},
        "review.reorder": {"trackIds": tracks[::-1]},
        "review.extend": {"targetTrackCount": 6},
        "review.undo": {},
        "review.redo": {},
    }[method]
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute(method, {"reviewId": review_id, **params})
    assert error.value.code == "stale_review"
    assert state(backend) == before


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_a_chat_apply_refuses_a_list_track_changed_on_disk(chat_setup, mutation: str) -> None:
    facade, transport, backend, _, _ = chat_setup
    transport.reply = answer(replace_at(2))
    action = turn(facade, backend.review_id)["result"]["actions"][0]
    mutate(backend.review.recommendation.ordered_tracks[1].path, mutation)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        call(facade, "ai.chat.apply", {"actionId": action["actionId"]})
    # Today the assistant reports its own refusal code for a list that moved under it.
    assert error.value.code == "stale_ai"
    assert state(backend) == before


def test_a_compared_replacement_changed_on_disk_is_refused_and_changes_nothing(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    tracks = [track["id"] for track in result["tracks"]]
    comparison = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": tracks[2]})
    offered = comparison["replacement"]["id"]
    Path(next(record.path for record in records if identity(record) == offered)).write_bytes(b"changed after compare")
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.replace",
            {"reviewId": comparison["reviewId"], "trackId": tracks[2], "replacementId": offered},
        )
    assert error.value.code == "stale_review"
    assert state(backend) == before


def test_a_candidate_changed_on_disk_is_never_offered_by_a_comparison(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    tracks = [track["id"] for track in result["tracks"]]
    target = tracks[2]
    offered = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": target})["replacement"][
        "id"
    ]
    Path(next(record.path for record in records if identity(record) == offered)).write_bytes(b"changed after compare")
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": target})
    assert error.value.code == "stale_review"
    assert state(backend) == before
    assert offered not in [
        track["id"] for track in backend.execute("review.details", {"reviewId": result["reviewId"]})["tracks"]
    ]


def test_a_candidate_changed_on_disk_is_never_added_by_an_extension(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    listed = {track.path for track in backend.review.recommendation.ordered_tracks}
    for record in records:
        if record.path not in listed:
            Path(record.path).write_bytes(b"changed after generation")
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.extend", {"reviewId": result["reviewId"], "targetTrackCount": 6})
    assert error.value.code == "stale_review"
    assert state(backend) == before
    listed_after = [
        track["id"] for track in backend.execute("review.details", {"reviewId": result["reviewId"]})["tracks"]
    ]
    assert listed_after == [track["id"] for track in result["tracks"]]
