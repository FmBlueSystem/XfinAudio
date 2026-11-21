"""Saving the list in progress back to the saved playlist it was opened from (S3, S6).

``playlist.save_review`` takes exactly the review identity and writes the current
order into the same playlist with the compare-and-update every save uses: a playlist
that changed elsewhere is refused with ``stale_edit``, and nothing is written.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.library.models import TrackRecord


def saved_list(tmp_path: Path, count: int = 6) -> tuple[HeadlessBackend, list[TrackRecord], Any, dict[str, Any]]:
    """Open a saved playlist whose order is the reverse of the library order."""
    backend, records = seeded(tmp_path, count)
    order = [record.path for record in records][::-1]
    playlist = backend.playlists.create("Saved set", order)
    opened = backend.execute("playlist.open", {"playlistId": playlist.id})
    assert opened["editable"] is True
    return backend, records, playlist, opened


def ids(result: dict[str, Any]) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def paths_of(records: list[TrackRecord]) -> dict[str, str]:
    return {identity(record): record.path for record in records}


def remove_one(backend: HeadlessBackend, review: dict[str, Any], index: int = 1) -> dict[str, Any]:
    return backend.execute("review.remove", {"reviewId": review["reviewId"], "trackId": review["tracks"][index]["id"]})


def test_saving_a_saved_review_writes_the_current_order(tmp_path: Path) -> None:
    backend, records, playlist, opened = saved_list(tmp_path)
    removed = remove_one(backend, opened)
    new_order = ids(removed)[::-1]
    reordered = backend.execute("review.reorder", {"reviewId": removed["reviewId"], "trackIds": new_order})
    assert ids(reordered) == new_order

    saved = backend.execute("playlist.save_review", {"reviewId": reordered["reviewId"]})

    assert set(saved) == {"id", "name", "trackCount"}
    assert (saved["id"], saved["name"], saved["trackCount"]) == (playlist.id, "Saved set", len(new_order))
    by_id = paths_of(records)
    assert backend.playlists.get_by_id(playlist.id).track_paths == [by_id[item] for item in new_order]
    reopened = backend.execute("playlist.open", {"playlistId": playlist.id})
    assert reopened["editable"] is True
    assert ids(reopened) == new_order


def test_a_playlist_renamed_elsewhere_refuses_the_save(tmp_path: Path) -> None:
    backend, _, playlist, opened = saved_list(tmp_path)
    removed = remove_one(backend, opened)
    backend.playlists.update_name(playlist.id, "Renamed elsewhere")
    before = backend.playlists.get_by_id(playlist.id)

    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save_review", {"reviewId": removed["reviewId"]})

    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id) == before
    assert backend.playlists.get_by_id(playlist.id).track_paths == playlist.track_paths


def test_a_playlist_changed_by_another_save_refuses_the_save(tmp_path: Path) -> None:
    backend, records, playlist, opened = saved_list(tmp_path)
    removed = remove_one(backend, opened)
    elsewhere = [record.path for record in records][:3]
    backend.playlists.update_tracks(playlist.id, elsewhere)

    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save_review", {"reviewId": removed["reviewId"]})

    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id).track_paths == elsewhere


def test_a_generated_review_cannot_be_saved_back_to_a_playlist(tmp_path: Path) -> None:
    backend, _, playlist, _ = saved_list(tmp_path)
    before = backend.playlists.get_by_id(playlist.id)
    generated = backend.execute("prep.generate", {"targetTrackCount": 3})

    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save_review", {"reviewId": generated["reviewId"]})

    assert error.value.code == "stale_review"
    assert backend.playlists.get_by_id(playlist.id) == before


def test_a_superseded_review_id_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    backend, _, playlist, opened = saved_list(tmp_path)
    before = backend.playlists.get_by_id(playlist.id)
    removed = remove_one(backend, opened)
    assert removed["reviewId"] != opened["reviewId"]

    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save_review", {"reviewId": opened["reviewId"]})

    assert error.value.code == "stale_review"
    assert backend.playlists.get_by_id(playlist.id) == before
    # The current identity still saves, so the refusal belongs to the superseded one.
    assert backend.execute("playlist.save_review", {"reviewId": removed["reviewId"]})["trackCount"] == 5


def test_a_track_of_the_list_changed_on_disk_refuses_the_save(tmp_path: Path) -> None:
    backend, records, playlist, opened = saved_list(tmp_path)
    before = backend.playlists.get_by_id(playlist.id)
    removed = remove_one(backend, opened)
    Path(records[0].path).unlink()

    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save_review", {"reviewId": removed["reviewId"]})
    with pytest.raises(BackendError) as other:
        backend.execute("playlist.save", {"name": "Copy", "reviewId": removed["reviewId"]})

    assert error.value.code == "stale_review"
    assert error.value.code == other.value.code
    assert backend.playlists.get_by_id(playlist.id) == before


def test_saving_twice_keeps_writing_the_same_playlist(tmp_path: Path) -> None:
    backend, records, playlist, opened = saved_list(tmp_path)
    first = remove_one(backend, opened)

    first_saved = backend.execute("playlist.save_review", {"reviewId": first["reviewId"]})
    again = backend.execute("playlist.save_review", {"reviewId": first["reviewId"]})
    second = remove_one(backend, first)
    second_saved = backend.execute("playlist.save_review", {"reviewId": second["reviewId"]})

    assert first_saved["trackCount"] == again["trackCount"] == 5
    assert second_saved["id"] == playlist.id
    assert second_saved["trackCount"] == 4
    assert backend.playlists.get_by_id(playlist.id).track_paths == [paths_of(records)[item] for item in ids(second)]


def test_saving_as_a_new_playlist_keeps_its_existing_path(tmp_path: Path) -> None:
    backend, records, playlist, opened = saved_list(tmp_path)
    removed = remove_one(backend, opened)

    new = backend.execute("playlist.save", {"name": "Copy", "reviewId": removed["reviewId"]})

    assert new["id"] != playlist.id
    assert new["name"] == "Copy"
    assert backend.playlists.get_by_id(new["id"]).track_paths == [paths_of(records)[item] for item in ids(removed)]
    assert backend.playlists.get_by_id(playlist.id).track_paths == [record.path for record in records][::-1]
