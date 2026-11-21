"""A saved playlist opened as the list in progress survives a restart (S3).

A saved list is recovered like a generated one, still tied to the playlist it was
opened from: every review command keeps working on it, ``playlist.save_review`` keeps
writing back while that playlist is still the one the list was compared against, and a
playlist deleted or changed meanwhile still restores the list but refuses the save with
``stale_edit``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.review_store import FIELDS, VERSION, store_path
from xfinaudio.library.models import TrackRecord


def stored_backend(backend: HeadlessBackend) -> HeadlessBackend:
    """Restart the core the way the app does: the roots are the ones a scan authorized."""
    (backend.data_dir / "roots.json").write_text(json.dumps([str(root) for root in backend.roots]), encoding="utf-8")
    return HeadlessBackend(backend.data_dir)


def opened(tmp_path: Path, count: int = 8, listed: int = 4) -> tuple[HeadlessBackend, list[TrackRecord], Any, dict]:
    """Open a saved playlist whose order is the reverse of the list it holds."""
    backend, records = seeded(tmp_path, count)
    order = [record.path for record in records][:listed][::-1]
    playlist = backend.playlists.create("Saved set", order)
    review = backend.execute("playlist.open", {"playlistId": playlist.id})
    assert review["editable"] is True
    assert review["variant"] == "saved"
    return backend, records, playlist, review


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def stored(backend: HeadlessBackend) -> dict:
    return json.loads(store_path(backend.data_dir).read_text(encoding="utf-8"))


def test_an_edited_saved_list_is_recovered_tied_to_its_playlist(tmp_path: Path) -> None:
    backend, _, playlist, review = opened(tmp_path)
    reordered = backend.execute("review.reorder", {"reviewId": review["reviewId"], "trackIds": ids(review)[::-1]})
    before = backend.execute("review.details", {"reviewId": reordered["reviewId"]})
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert resumed["available"] is True
    assert resumed["dropped"] is False
    restored = resumed["review"]
    assert (restored["variant"], restored["savedPlaylistId"], restored["editable"]) == ("saved", playlist.id, True)
    assert restored["reviewId"] == reordered["reviewId"]
    assert ids(restored) == ids(reordered)
    assert {key: value for key, value in restored.items() if key not in ("canUndo", "canRedo")} == {
        key: value for key, value in before.items() if key not in ("canUndo", "canRedo")
    }
    # A saved list protects nothing and never names the files behind its tracks.
    assert restored["protectedTrackIds"] == []
    assert str(tmp_path) not in json.dumps(resumed)
    # The restored list is the live one: every review command keeps working on it.
    details = restarted.execute("review.details", {"reviewId": restored["reviewId"]})
    assert (details["savedPlaylistId"], ids(details)) == (playlist.id, ids(restored))
    continued = restarted.execute("review.reorder", {"reviewId": restored["reviewId"], "trackIds": ids(restored)})
    assert continued["reviewId"] != restored["reviewId"]
    assert (continued["variant"], continued["savedPlaylistId"]) == ("saved", playlist.id)
    undone = restarted.execute("review.undo", {"reviewId": continued["reviewId"]})
    assert ids(undone) == ids(restored)
    with pytest.raises(BackendError) as error:
        restarted.execute("review.undo", {"reviewId": undone["reviewId"]})
    assert error.value.code == "nothing_to_undo"


def test_a_restored_saved_list_saves_back_to_its_playlist(tmp_path: Path) -> None:
    backend, records, playlist, review = opened(tmp_path)
    restarted = stored_backend(backend)
    restored = restarted.execute("review.resume", {})["review"]
    assert ids(restored) == ids(review)
    removed = restarted.execute(
        "review.remove", {"reviewId": restored["reviewId"], "trackId": restored["tracks"][1]["id"]}
    )
    saved = restarted.execute("playlist.save_review", {"reviewId": removed["reviewId"]})
    assert set(saved) == {"id", "name", "trackCount"}
    assert (saved["id"], saved["name"], saved["trackCount"]) == (playlist.id, "Saved set", len(ids(removed)))
    by_id = {identity(record): record.path for record in records}
    assert restarted.playlists.get_by_id(playlist.id).track_paths == [by_id[item] for item in ids(removed)]
    # The saved version the review is compared against was stored too: a second restart
    # saves the very same order back without calling it stale.
    again = stored_backend(restarted)
    resumed = again.execute("review.resume", {})["review"]
    assert ids(resumed) == ids(removed)
    again_saved = again.execute("playlist.save_review", {"reviewId": resumed["reviewId"]})
    assert (again_saved["id"], again_saved["trackCount"]) == (playlist.id, len(ids(removed)))


@pytest.mark.parametrize("mutation", ["deleted", "renamed", "retracked"])
def test_a_playlist_changed_meanwhile_is_restored_but_the_save_is_stale(tmp_path: Path, mutation: str) -> None:
    backend, records, playlist, review = opened(tmp_path)
    if mutation == "deleted":
        backend.playlists.delete(playlist.id)
    elif mutation == "renamed":
        backend.playlists.update_name(playlist.id, "Renamed elsewhere")
    else:
        backend.playlists.update_tracks(playlist.id, [record.path for record in records[:2]])
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert resumed["available"] is True
    restored = resumed["review"]
    assert (restored["savedPlaylistId"], ids(restored)) == (playlist.id, ids(review))
    with pytest.raises(BackendError) as error:
        restarted.execute("playlist.save_review", {"reviewId": restored["reviewId"]})
    assert error.value.code == "stale_edit"


def test_the_saved_review_is_stored_tied_to_its_playlist(tmp_path: Path) -> None:
    backend, _, playlist, _ = opened(tmp_path)
    payload = stored(backend)
    assert payload["version"] == VERSION
    assert set(payload) == set(FIELDS) | {"savedPlaylist"}
    assert payload["variant"] == "saved"
    assert set(payload["savedPlaylist"]) == {"id", "name", "createdAt", "updatedAt", "trackPaths"}
    assert (payload["savedPlaylist"]["id"], payload["savedPlaylist"]["name"]) == (playlist.id, "Saved set")
    assert payload["savedPlaylist"]["trackPaths"] == playlist.track_paths


def test_a_generated_review_keeps_the_contract_it_had(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    generated = backend.execute("prep.generate", {"targetTrackCount": 4})
    payload = stored(backend)
    assert set(payload) == set(FIELDS)
    # The file a build before this change wrote is still restored: same facts, version 1.
    payload["version"] = 1
    store_path(backend.data_dir).write_text(json.dumps(payload), encoding="utf-8")
    resumed = stored_backend(backend).execute("review.resume", {})
    assert resumed["available"] is True
    assert resumed["review"]["reviewId"] == generated["reviewId"]
    assert [track["id"] for track in resumed["review"]["tracks"]] == [track["id"] for track in generated["tracks"]]


@pytest.mark.parametrize("mutation", ["missing_playlist", "unknown_id", "no_paths_field", "generated_with_playlist"])
def test_a_saved_payload_outside_the_contract_is_ignored_and_logged(
    tmp_path: Path, mutation: str, caplog: pytest.LogCaptureFixture
) -> None:
    backend, *_ = opened(tmp_path)
    payload = stored(backend)
    if mutation == "missing_playlist":
        del payload["savedPlaylist"]
    elif mutation == "unknown_id":
        payload["savedPlaylist"]["id"] = "1"
    elif mutation == "no_paths_field":
        del payload["savedPlaylist"]["trackPaths"]
    else:
        payload["variant"] = "balanced"
    store_path(backend.data_dir).write_text(json.dumps(payload), encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        restarted = stored_backend(backend)
    assert caplog.records, "an out-of-contract saved payload must leave a warning"
    assert restarted.execute("review.resume", {}) == {"available": False, "review": None, "dropped": False}
