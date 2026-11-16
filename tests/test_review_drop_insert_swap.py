"""Drop, insert and swap a chosen track in the generated review (S3)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from tests.test_headless_prep_parity import identity, seeded
from tests.test_review_extend import stored_backend
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.review_store import read_review
from xfinaudio.library.models import TrackRecord

MUTATIONS = ("changed", "moved", "deleted")


def generated(tmp_path: Path, count: int = 10, target: int = 4) -> tuple[HeadlessBackend, list, dict]:
    backend, records = seeded(tmp_path, count)
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": target})


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def state(backend: HeadlessBackend) -> tuple[object, ...]:
    """Everything a refused edit must leave exactly as it found it."""
    return (
        backend.review,
        backend.review_id,
        list(backend.review_actions.history),
        list(backend.review_actions.future),
        dict(backend.review_actions.offers),
        backend.review_actions.removed,
    )


def stored(backend: HeadlessBackend) -> dict:
    payload = read_review(backend.data_dir)
    assert payload is not None
    return payload


def spare(backend: HeadlessBackend, records: list[TrackRecord], offset: int = 0) -> TrackRecord:
    """A library record the current list does not hold."""
    listed = {track.path for track in backend.review.recommendation.ordered_tracks}
    others = [record for record in records if record.path not in listed]
    return others[offset]


def mutate(path: str, mutation: str) -> None:
    target = Path(path)
    if mutation == "changed":
        target.write_bytes(b"changed after generation")
    elif mutation == "moved":
        target.rename(target.with_name(target.name + ".moved"))
    else:
        target.unlink()


def test_drop_takes_the_track_out_without_a_replacement_and_is_one_undo_step(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = ids(result)
    dropped = backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": original[1]})
    assert ids(dropped) == [original[0], original[2], original[3]]
    assert dropped["reviewId"] != result["reviewId"]
    assert (dropped["canUndo"], dropped["canRedo"]) == (True, False)
    # The answer is the live review, stored under its own revision.
    assert backend.execute("review.details", {"reviewId": dropped["reviewId"]}) == dropped
    assert stored(backend)["reviewId"] == dropped["reviewId"]
    undone = backend.execute("review.undo", {"reviewId": dropped["reviewId"]})
    assert ids(undone) == original
    assert undone["reviewId"] not in {result["reviewId"], dropped["reviewId"]}
    assert (undone["canUndo"], undone["canRedo"]) == (False, True)
    redone = backend.execute("review.redo", {"reviewId": undone["reviewId"]})
    assert ids(redone) == [original[0], original[2], original[3]]


def test_drop_refuses_a_protected_track(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute(
        "prep.generate",
        {"targetTrackCount": 4, "startTrackId": identity(records[0]), "requiredTrackIds": [identity(records[1])]},
    )
    before = state(backend)
    for track in records[:2]:
        with pytest.raises(BackendError) as error:
            backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": identity(track)})
        assert error.value.code == "protected_track"
    assert state(backend) == before


def test_drop_refuses_to_leave_fewer_than_two_tracks(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path, target=2)
    tracks = ids(result)
    assert len(tracks) == 2
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": tracks[0]})
    assert error.value.code == "invalid_params"
    assert state(backend) == before
    # One track more is the boundary: the same call is accepted there.
    (tmp_path / "three").mkdir()
    three, _, longer = generated(tmp_path / "three", target=3)
    assert len(ids(longer)) == 3
    shortened = three.execute("review.drop", {"reviewId": longer["reviewId"], "trackId": ids(longer)[0]})
    assert len(ids(shortened)) == 2


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_a_drop_refuses_a_listed_track_changed_on_disk(tmp_path: Path, mutation: str) -> None:
    backend, _, result = generated(tmp_path)
    mutate(backend.review.recommendation.ordered_tracks[1].path, mutation)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": ids(result)[1]})
    assert error.value.code == "stale_review"
    assert state(backend) == before


def test_a_dropped_track_joins_the_removed_set_and_may_come_back(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    dropped = ids(result)[1]
    path = backend.review.recommendation.ordered_tracks[1].path
    after = backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": dropped})
    assert dropped not in ids(after)
    assert stored(backend)["removed"] == [path]
    # A growth that picks candidates never brings it back.
    grew = backend.execute("review.extend", {"reviewId": after["reviewId"], "targetTrackCount": 7})
    assert dropped not in ids(grew)
    assert stored(backend)["removed"] == [path]
    # An insert does, and the track leaves the removed set.
    back = backend.execute("review.insert", {"reviewId": grew["reviewId"], "trackId": dropped, "position": 1})
    assert ids(back)[0] == dropped
    assert stored(backend)["removed"] == []


@pytest.mark.parametrize("position", [1, 2, 5])
def test_insert_puts_a_library_track_at_the_requested_position_and_is_one_undo_step(
    tmp_path: Path, position: int
) -> None:
    backend, records, result = generated(tmp_path)
    original = ids(result)
    wanted = identity(spare(backend, records))
    inserted = backend.execute(
        "review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": position}
    )
    expected = [*original[: position - 1], wanted, *original[position - 1 :]]
    assert ids(inserted) == expected
    assert len(expected) == len(original) + 1
    assert inserted["reviewId"] != result["reviewId"]
    assert (inserted["canUndo"], inserted["canRedo"]) == (True, False)
    assert backend.execute("review.details", {"reviewId": inserted["reviewId"]}) == inserted
    assert stored(backend)["reviewId"] == inserted["reviewId"]
    undone = backend.execute("review.undo", {"reviewId": inserted["reviewId"]})
    assert ids(undone) == original
    assert (undone["canUndo"], undone["canRedo"]) == (False, True)
    assert ids(backend.execute("review.redo", {"reviewId": undone["reviewId"]})) == expected


@pytest.mark.parametrize("position", [0, -1, 6, 7, 5.0, True, "1", None])
def test_an_out_of_range_insert_position_is_invalid_params(tmp_path: Path, position: object) -> None:
    backend, records, result = generated(tmp_path)
    wanted = identity(spare(backend, records))
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": position})
    assert error.value.code == "invalid_params"
    assert state(backend) == before


def test_insert_and_swap_need_a_track_with_complete_metadata(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    incomplete = records[7].model_copy(update={"metadata_status": "incomplete"})
    backend.repository.save_scan_results([*records[:7], incomplete])
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    assert identity(incomplete) not in ids(result)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.insert", {"reviewId": result["reviewId"], "trackId": identity(incomplete), "position": 1}
        )
    assert error.value.code == "invalid_params"
    assert state(backend) == before
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.swap",
            {"reviewId": result["reviewId"], "trackId": ids(result)[1], "replacementTrackId": identity(incomplete)},
        )
    assert error.value.code == "invalid_params"
    assert state(backend) == before


def test_insert_and_swap_never_use_a_track_the_plan_excluded(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "excludedTrackIds": [identity(records[7])]})
    assert identity(records[7]) not in ids(result)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.insert", {"reviewId": result["reviewId"], "trackId": identity(records[7]), "position": 1}
        )
    assert error.value.code == "invalid_params"
    assert state(backend) == before
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.swap",
            {"reviewId": result["reviewId"], "trackId": ids(result)[1], "replacementTrackId": identity(records[7])},
        )
    assert error.value.code == "invalid_params"
    assert state(backend) == before


def test_insert_never_goes_before_the_protected_opening(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "startTrackId": identity(records[0])})
    assert ids(result)[0] == identity(records[0])
    wanted = identity(spare(backend, records))
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": 1})
    assert error.value.code == "protected_track"
    assert state(backend) == before
    at_two = backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": 2})
    assert ids(at_two)[:2] == [identity(records[0]), wanted]


def test_insert_never_goes_after_the_protected_closing(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "endTrackId": identity(records[2])})
    assert ids(result)[-1] == identity(records[2])
    wanted = identity(spare(backend, records))
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": 5})
    assert error.value.code == "protected_track"
    assert state(backend) == before
    at_four = backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": 4})
    assert ids(at_four)[3] == wanted
    assert ids(at_four)[-1] == identity(records[2])


def test_insert_never_goes_inside_the_manual_prefix(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute(
        "prep.generate", {"targetTrackCount": 4, "requiredTrackIds": [identity(records[1]), identity(records[3])]}
    )
    assert ids(result)[:2] == [identity(records[1]), identity(records[3])]
    wanted = identity(spare(backend, records))
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": 2})
    assert error.value.code == "protected_track"
    assert state(backend) == before
    after_prefix = backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": 3})
    assert ids(after_prefix)[:3] == [identity(records[1]), identity(records[3]), wanted]


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_insert_refuses_a_library_track_changed_on_disk(tmp_path: Path, mutation: str) -> None:
    backend, records, result = generated(tmp_path)
    wanted = spare(backend, records)
    mutate(wanted.path, mutation)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": identity(wanted), "position": 2})
    assert error.value.code == "stale_review"
    assert state(backend) == before


def test_an_insert_never_takes_the_list_past_one_hundred_tracks(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 101)
    result = backend.execute("prep.generate", {"targetTrackCount": 100})
    listed = ids(result)
    assert len(listed) == 100
    wanted = next(record for record in records if identity(record) not in listed)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": identity(wanted), "position": 1})
    assert error.value.code == "invalid_params"
    assert state(backend) == before
    assert ids(backend.execute("review.details", {"reviewId": result["reviewId"]})) == listed


def test_swap_replaces_a_track_with_a_library_track_at_the_same_position_and_is_one_undo_step(
    tmp_path: Path,
) -> None:
    backend, records, result = generated(tmp_path)
    original = ids(result)
    wanted = identity(spare(backend, records))
    swapped = backend.execute(
        "review.swap",
        {"reviewId": result["reviewId"], "trackId": original[2], "replacementTrackId": wanted},
    )
    expected = [original[0], original[1], wanted, original[3]]
    assert ids(swapped) == expected
    assert len(ids(swapped)) == len(original)
    assert swapped["reviewId"] != result["reviewId"]
    assert (swapped["canUndo"], swapped["canRedo"]) == (True, False)
    assert backend.execute("review.details", {"reviewId": swapped["reviewId"]}) == swapped
    assert stored(backend)["reviewId"] == swapped["reviewId"]
    undone = backend.execute("review.undo", {"reviewId": swapped["reviewId"]})
    assert ids(undone) == original
    assert (undone["canUndo"], undone["canRedo"]) == (False, True)
    assert ids(backend.execute("review.redo", {"reviewId": undone["reviewId"]})) == expected


def test_a_swap_refuses_to_take_out_a_protected_track(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute(
        "prep.generate",
        {"targetTrackCount": 4, "startTrackId": identity(records[0]), "requiredTrackIds": [identity(records[1])]},
    )
    wanted = identity(spare(backend, records, 1))
    before = state(backend)
    for track in records[:2]:
        with pytest.raises(BackendError) as error:
            backend.execute(
                "review.swap",
                {"reviewId": result["reviewId"], "trackId": identity(track), "replacementTrackId": wanted},
            )
        assert error.value.code == "protected_track"
    assert state(backend) == before


def test_a_swap_refuses_a_track_already_in_the_list(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = ids(result)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.swap",
            {"reviewId": result["reviewId"], "trackId": original[0], "replacementTrackId": original[2]},
        )
    assert error.value.code == "invalid_params"
    assert state(backend) == before


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_a_swap_refuses_an_incoming_track_changed_on_disk(tmp_path: Path, mutation: str) -> None:
    backend, records, result = generated(tmp_path)
    wanted = spare(backend, records)
    mutate(wanted.path, mutation)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.swap",
            {"reviewId": result["reviewId"], "trackId": ids(result)[1], "replacementTrackId": identity(wanted)},
        )
    assert error.value.code == "stale_review"
    assert state(backend) == before


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_a_swap_refuses_a_listed_track_changed_on_disk(tmp_path: Path, mutation: str) -> None:
    backend, records, result = generated(tmp_path)
    wanted = identity(spare(backend, records))
    mutate(backend.review.recommendation.ordered_tracks[1].path, mutation)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.swap",
            {"reviewId": result["reviewId"], "trackId": ids(result)[1], "replacementTrackId": wanted},
        )
    assert error.value.code == "stale_review"
    assert state(backend) == before


def test_an_unknown_track_id_is_invalid_params(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    original = ids(result)
    unknown = str(uuid4())
    wanted = identity(spare(backend, records))
    for method, params in (
        ("review.drop", {"trackId": unknown}),
        ("review.insert", {"trackId": unknown, "position": 1}),
        ("review.swap", {"trackId": original[0], "replacementTrackId": unknown}),
        ("review.swap", {"trackId": unknown, "replacementTrackId": wanted}),
    ):
        before = state(backend)
        with pytest.raises(BackendError) as error:
            backend.execute(method, {"reviewId": result["reviewId"], **params})
        assert error.value.code == "invalid_params"
        assert state(backend) == before


def test_drop_insert_and_swap_require_exactly_the_contract_fields(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    original = ids(result)
    wanted = identity(spare(backend, records))
    review_id = result["reviewId"]
    for method, params in (
        ("review.drop", {"reviewId": review_id}),
        ("review.drop", {"reviewId": review_id, "trackId": original[0], "position": 1}),
        ("review.insert", {"reviewId": review_id, "trackId": wanted}),
        ("review.insert", {"reviewId": review_id, "trackId": wanted, "position": 1, "replacementTrackId": wanted}),
        ("review.swap", {"reviewId": review_id, "trackId": original[0]}),
        (
            "review.swap",
            {"reviewId": review_id, "trackId": original[0], "replacementTrackId": wanted, "position": 2},
        ),
    ):
        before = state(backend)
        with pytest.raises(BackendError) as error:
            backend.execute(method, params)
        assert error.value.code == "invalid_params"
        assert state(backend) == before


def test_a_restart_recovers_a_dropped_list_and_keeps_the_track_out(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    dropped = ids(result)[1]
    path = backend.review.recommendation.ordered_tracks[1].path
    after = backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": dropped})
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert (resumed["available"], resumed["dropped"]) == (True, False)
    assert resumed["review"]["reviewId"] == after["reviewId"]
    assert ids(resumed["review"]) == ids(after)
    assert (resumed["review"]["canUndo"], resumed["review"]["canRedo"]) == (False, False)
    assert str(tmp_path) not in json.dumps(resumed)
    assert stored(restarted)["removed"] == [path]
    grew = restarted.execute("review.extend", {"reviewId": after["reviewId"], "targetTrackCount": 7})
    assert dropped not in ids(grew)


def test_a_restart_recovers_an_inserted_list(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    original = ids(result)
    wanted = identity(spare(backend, records))
    inserted = backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": wanted, "position": 2})
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert (resumed["available"], resumed["dropped"]) == (True, False)
    assert resumed["review"]["reviewId"] == inserted["reviewId"]
    assert ids(resumed["review"]) == [original[0], wanted, original[1], original[2], original[3]]
    dropped = restarted.execute("review.drop", {"reviewId": inserted["reviewId"], "trackId": wanted})
    assert ids(dropped) == original
    assert stored(restarted)["removed"] == [backend.review.recommendation.ordered_tracks[1].path]


def test_a_restart_recovers_a_swapped_list_and_its_removed_set(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    original = ids(result)
    outgoing = backend.review.recommendation.ordered_tracks[2].path
    wanted = identity(spare(backend, records))
    swapped = backend.execute(
        "review.swap", {"reviewId": result["reviewId"], "trackId": original[2], "replacementTrackId": wanted}
    )
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert (resumed["available"], resumed["dropped"]) == (True, False)
    assert resumed["review"]["reviewId"] == swapped["reviewId"]
    assert ids(resumed["review"]) == [original[0], original[1], wanted, original[3]]
    assert stored(restarted)["removed"] == [outgoing]
    back = restarted.execute("review.insert", {"reviewId": swapped["reviewId"], "trackId": original[2], "position": 3})
    assert ids(back) == [original[0], original[1], original[2], wanted, original[3]]
    assert stored(restarted)["removed"] == []
