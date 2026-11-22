"""A review edit still checks every library file it may pick from (S3).

Only the assistant context decides among library tracks without reading their files; a
review edit keeps checking the whole library on disk, so a deleted library track leaves
the candidate pool exactly as it did before and the answers are the same ones.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.test_headless_ai_context import setup as setup  # noqa: F401
from xfinaudio.headless.common import BackendError, _public_track

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend


def listed(backend: HeadlessBackend) -> set[str]:
    return {track.path for track in backend.review.recommendation.ordered_tracks}  # type: ignore[union-attr]


def unlisted(backend: HeadlessBackend, root: Path) -> list[Path]:
    """The library files this review does not list, the metadata gap fixture aside."""
    current = listed(backend)
    return [
        path
        for path in sorted(root.iterdir())
        if path.suffix == ".flac" and str(path) not in current and path.name != "gap.flac"
    ]


def test_extending_still_succeeds_after_an_unlisted_library_file_is_deleted(setup) -> None:
    backend, selectors, root = setup
    review_id = selectors["review"]["reviewId"]
    assert len(backend.review.recommendation.ordered_tracks) == 4
    unlisted(backend, root)[0].unlink()

    extended = backend.execute("review.extend", {"reviewId": review_id, "targetTrackCount": 5})

    assert len(extended["tracks"]) == 5


def test_replace_still_refuses_the_offer_after_the_offered_file_is_deleted(setup) -> None:
    backend, selectors, root = setup
    review_id = selectors["review"]["reviewId"]
    target = backend.review.recommendation.ordered_tracks[1]
    offered = backend.execute("review.compare", {"reviewId": review_id, "trackId": _public_track(target)["id"]})[
        "replacement"
    ]
    assert offered is not None
    offered_path = next(
        record.path for record in backend.repository.list_tracks() if _public_track(record)["id"] == offered["id"]
    )
    Path(offered_path).unlink()

    with pytest.raises(BackendError) as refused:
        backend.execute(
            "review.replace",
            {"reviewId": review_id, "trackId": _public_track(target)["id"], "replacementId": offered["id"]},
        )

    # Today the pool no longer holds the deleted offer, so the proposal moved on.
    assert refused.value.code == "stale_review"
    assert str(refused.value) == "Compare this track again and use the replacement it offered"


def test_inserting_still_refuses_a_deleted_library_track_as_it_did(setup) -> None:
    backend, selectors, root = setup
    review_id = selectors["review"]["reviewId"]
    gone = unlisted(backend, root)[0]
    gone_id = next(
        _public_track(record)["id"] for record in backend.repository.list_tracks() if record.path == str(gone)
    )
    gone.unlink()

    with pytest.raises(BackendError) as refused:
        backend.execute("review.insert", {"reviewId": review_id, "trackId": gone_id, "position": 2})

    # Today the chosen track left the library, and that is what the refusal says.
    assert refused.value.code == "stale_review"
    assert str(refused.value) == "The chosen track changed on disk; prepare a current review"
