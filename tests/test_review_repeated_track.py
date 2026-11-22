"""A list that holds the same track twice can be reordered (small fixes S1).

A track's id comes from its path, so both copies of a repeated track share one id.
A reorder therefore names each current id as many times as the list holds it; any
other count still fails closed and leaves the list untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_prep_parity import seeded
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def opened_with_repeat(tmp_path: Path) -> tuple[HeadlessBackend, dict]:
    backend, records = seeded(tmp_path, 6)
    a, b, c = (record.path for record in records[:3])
    playlist = backend.playlists.create("Repeated", [a, b, a, c])
    assert playlist.id is not None
    review = backend.execute("playlist.open", {"playlistId": playlist.id})
    assert review["editable"] is True
    return backend, review


def test_a_repeated_track_is_moved_to_another_position(tmp_path: Path) -> None:
    backend, review = opened_with_repeat(tmp_path)
    a, b, _, c = ids(review)
    assert ids(review)[2] == a
    moved = backend.execute("review.reorder", {"reviewId": review["reviewId"], "trackIds": [a, b, c, a]})
    assert ids(moved) == [a, b, c, a]
    details = backend.execute("review.details", {"reviewId": moved["reviewId"]})
    assert ids(details) == [a, b, c, a]


def test_an_order_that_changes_how_often_a_track_appears_is_refused(tmp_path: Path) -> None:
    backend, review = opened_with_repeat(tmp_path)
    a, b, _, c = ids(review)
    before = backend.review, backend.review_id
    for drifted in ([a, b, c, c], [a, b, c], [a, b, a, c, a]):
        with pytest.raises(BackendError) as error:
            backend.execute("review.reorder", {"reviewId": review["reviewId"], "trackIds": drifted})
        assert error.value.code == "invalid_params"
    assert backend.review is before[0]
    assert backend.review_id == before[1]
    assert ids(backend.execute("review.details", {"reviewId": review["reviewId"]})) == [a, b, a, c]
