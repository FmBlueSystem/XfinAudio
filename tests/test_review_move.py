"""Move a generated track to any position with one call (S3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.common import BackendError
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import recommendation_reordered


def generated(tmp_path: Path, count: int = 6) -> tuple[object, list, dict]:
    backend, records = seeded(tmp_path, count)
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": 4})


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def moved(order: list[str], target: int, position: int) -> list[str]:
    """The full order the «Mover» control sends: take the track out, insert it at 1..N."""
    item = order[target]
    rest = [other for index, other in enumerate(order) if index != target]
    return [*rest[: position - 1], item, *rest[position - 1 :]]


def test_a_jump_of_several_positions_moves_the_track_and_is_undoable(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = ids(result)
    before = backend.review.recommendation
    paths = [track.path for track in before.ordered_tracks]
    # Four tracks: the last one jumps to the first position, three positions up.
    target = moved(original, 3, 1)
    assert target != original
    expected = recommendation_reordered(
        before,
        [paths[original.index(track)] for track in target],
        spectral_cohesion=backend.preferences.spectral_cohesion(),
    )
    jumped = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": target})
    assert ids(jumped) == target
    assert backend.review.recommendation == expected
    assert jumped["qualityScore"] == build_quality_report(expected).average_transition_score
    assert jumped["reviewId"] not in {result["reviewId"]}
    assert (jumped["canUndo"], jumped["canRedo"]) == (True, False)
    undone = backend.execute("review.undo", {"reviewId": jumped["reviewId"]})
    assert ids(undone) == original
    assert backend.review.recommendation == before
    assert undone["reviewId"] not in {result["reviewId"], jumped["reviewId"]}
    assert (undone["canUndo"], undone["canRedo"]) == (False, True)
    redone = backend.execute("review.redo", {"reviewId": undone["reviewId"]})
    assert ids(redone) == target


def test_each_jump_down_or_up_is_one_undo_step(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = ids(result)
    down = moved(original, 0, 4)
    assert down == [*original[1:], original[0]]
    first = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": down})
    middle = moved(down, 3, 2)
    assert ids(first) == down
    second = backend.execute("review.reorder", {"reviewId": first["reviewId"], "trackIds": middle})
    assert ids(second) == middle
    assert len({result["reviewId"], first["reviewId"], second["reviewId"]}) == 3
    restored = backend.execute("review.undo", {"reviewId": second["reviewId"]})
    assert ids(restored) == down
    oldest = backend.execute("review.undo", {"reviewId": restored["reviewId"]})
    assert ids(oldest) == original
    assert oldest["canUndo"] is False
    assert oldest["canRedo"] is True


def test_an_out_of_range_position_or_a_displaced_protected_track_is_refused_and_changes_nothing(
    tmp_path: Path,
) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "startTrackId": identity(records[0])})
    original = ids(result)
    before = backend.review, backend.review_id
    # A position outside 1..N is refused by the renderer before it sends anything;
    # an order that cannot describe one position fails closed here.
    for drifted in (original[:3], [original[0], original[0], *original[2:]]):
        with pytest.raises(BackendError) as error:
            backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": drifted})
        assert error.value.code == "invalid_params"
    # The opening track is protected: it cannot be displaced from the first slot.
    with pytest.raises(BackendError) as error:
        backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": moved(original, 0, 4)})
    assert error.value.code == "protected_track"
    assert backend.review is before[0]
    assert backend.review_id == before[1]
    assert ids(backend.execute("review.details", {"reviewId": result["reviewId"]})) == original
