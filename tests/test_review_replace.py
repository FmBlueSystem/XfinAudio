"""Accept the compared replacement in the generated review (S2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.common import BackendError


def generated(tmp_path: Path, count: int = 8) -> tuple[object, list, dict]:
    backend, records = seeded(tmp_path, count)
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": 4})


def compared(backend, result: dict, index: int = 1) -> tuple[str, dict]:
    target = result["tracks"][index]["id"]
    return target, backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": target})


def test_replace_applies_exactly_the_compared_replacement_then_undo_restores_the_edit(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = [track["id"] for track in result["tracks"]]
    target, comparison = compared(backend, result)
    assert comparison["available"] is True
    offered = comparison["replacement"]["id"]
    assert offered not in original
    replaced = backend.execute(
        "review.replace", {"reviewId": result["reviewId"], "trackId": target, "replacementId": offered}
    )
    ids = [track["id"] for track in replaced["tracks"]]
    assert ids == [offered if item == target else item for item in original]
    assert replaced["reviewId"] not in {result["reviewId"], comparison["reviewId"]}
    assert replaced["canUndo"] is True
    assert replaced["canRedo"] is False
    undone = backend.execute("review.undo", {"reviewId": replaced["reviewId"]})
    assert [track["id"] for track in undone["tracks"]] == original
    assert undone["reviewId"] not in {result["reviewId"], replaced["reviewId"]}


def test_only_the_offered_replacement_is_accepted_and_a_refusal_changes_nothing(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = [track["id"] for track in result["tracks"]]
    target, comparison = compared(backend, result)
    offered = comparison["replacement"]["id"]
    before = backend.review, backend.review_id
    for replacement in (original[0], offered[:-1], "/Users/private/music.flac"):
        with pytest.raises(BackendError) as error:
            backend.execute(
                "review.replace", {"reviewId": result["reviewId"], "trackId": target, "replacementId": replacement}
            )
        assert error.value.code == "stale_review"
    assert backend.review_id == result["reviewId"]
    assert backend.review is before[0]
    assert [track["id"] for track in backend.execute("review.details", {"reviewId": result["reviewId"]})["tracks"]] == (
        original
    )


def test_a_replacement_needs_a_prior_compare_of_that_review_and_track(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    target, comparison = compared(backend, result)
    offered = comparison["replacement"]["id"]
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.replace",
            {"reviewId": result["reviewId"], "trackId": result["tracks"][2]["id"], "replacementId": offered},
        )
    assert error.value.code == "stale_review"
    reordered = backend.execute(
        "review.reorder", {"reviewId": result["reviewId"], "trackIds": [track["id"] for track in result["tracks"]]}
    )
    assert reordered["reviewId"] != result["reviewId"]
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.replace", {"reviewId": reordered["reviewId"], "trackId": target, "replacementId": offered}
        )
    assert error.value.code == "stale_review"


def test_an_unavailable_comparison_cannot_be_applied(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 6)
    outlier = {"bpm": 175, "camelot_key": "2B", "energy_level": 9}
    backend.repository.save_scan_results([*records[:4], *(record.model_copy(update=outlier) for record in records[4:])])
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    target, comparison = compared(backend, result)
    assert comparison["available"] is False
    assert comparison["replacement"] is None
    with pytest.raises(BackendError) as error:
        backend.execute(
            "review.replace", {"reviewId": result["reviewId"], "trackId": target, "replacementId": identity(records[4])}
        )
    assert error.value.code == "stale_review"
    assert backend.review_id == result["reviewId"]


def test_protected_tracks_keep_the_protected_track_code(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute(
        "prep.generate",
        {"targetTrackCount": 4, "startTrackId": identity(records[0]), "requiredTrackIds": [identity(records[1])]},
    )
    for track in records[:2]:
        with pytest.raises(BackendError) as error:
            backend.execute(
                "review.replace",
                {"reviewId": result["reviewId"], "trackId": identity(track), "replacementId": identity(records[7])},
            )
        assert error.value.code == "protected_track"
    assert backend.review_id == result["reviewId"]


def test_compare_stays_read_only_and_remove_still_reuses_its_own_replacement(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = [track["id"] for track in result["tracks"]]
    target, comparison = compared(backend, result)
    offered = comparison["replacement"]["id"]
    details = backend.execute("review.details", {"reviewId": result["reviewId"]})
    assert details["reviewId"] == result["reviewId"]
    assert [track["id"] for track in details["tracks"]] == original
    removed = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": target})
    ids = [track["id"] for track in removed["tracks"]]
    assert offered in ids
    assert target not in ids
    assert len(ids) == len(original)


def test_replace_requires_exactly_the_contract_fields(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    target, _ = compared(backend, result)
    for params in (
        {"reviewId": result["reviewId"], "trackId": target},
        {"reviewId": result["reviewId"], "trackId": target, "replacementId": target, "path": "/private"},
    ):
        with pytest.raises(BackendError) as error:
            backend.execute("review.replace", params)
        assert error.value.code == "invalid_params"
    assert backend.review_id == result["reviewId"]


def test_a_replaced_track_is_not_resurrected_by_a_later_removal(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    target, comparison = compared(backend, result)
    replaced = backend.execute(
        "review.replace",
        {"reviewId": result["reviewId"], "trackId": target, "replacementId": comparison["replacement"]["id"]},
    )
    removed = backend.execute(
        "review.remove", {"reviewId": replaced["reviewId"], "trackId": replaced["tracks"][0]["id"]}
    )
    ids = [track["id"] for track in removed["tracks"]]
    assert target not in ids
    assert len(ids) == len(replaced["tracks"])
