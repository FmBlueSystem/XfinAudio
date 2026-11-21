"""Undo and redo history for the generated review (S1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.common import BackendError


def generated(tmp_path: Path, count: int = 6) -> tuple[object, list, dict]:
    backend, records = seeded(tmp_path, count)
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": 4})


def swapped(result: dict, first: int = 0, second: int = 1) -> list[str]:
    ids = [track["id"] for track in result["tracks"]]
    ids[first], ids[second] = ids[second], ids[first]
    return ids


def test_undo_restores_tracks_and_unbans_the_removed_track(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 6)
    # Two out-of-band candidates can never backfill a 120 BPM slot, so the first
    # removal shortens the set and the restored track is the only eligible
    # replacement for the second removal.
    outlier = {"bpm": 175, "camelot_key": "2B", "energy_level": 9}
    backend.repository.save_scan_results([*records[:4], *(record.model_copy(update=outlier) for record in records[4:])])
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    tracks = [track["id"] for track in result["tracks"]]
    assert set(tracks) == {identity(record) for record in records[:4]}
    assert result["canUndo"] is False
    assert result["canRedo"] is False
    shortened = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": tracks[0]})
    assert [track["id"] for track in shortened["tracks"]] == tracks[1:]
    assert shortened["canUndo"] is True
    restored = backend.execute("review.undo", {"reviewId": shortened["reviewId"]})
    assert [track["id"] for track in restored["tracks"]] == tracks
    assert restored["reviewId"] not in {result["reviewId"], shortened["reviewId"]}
    assert restored["canUndo"] is False
    assert restored["canRedo"] is True
    backfilled = backend.execute("review.remove", {"reviewId": restored["reviewId"], "trackId": tracks[1]})
    assert [track["id"] for track in backfilled["tracks"]] != tracks[1:]
    assert tracks[0] in [track["id"] for track in backfilled["tracks"]]


def test_undo_and_redo_restore_order_and_mint_a_new_review_id(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = [track["id"] for track in result["tracks"]]
    reordered = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": original[::-1]})
    assert [track["id"] for track in reordered["tracks"]] == original[::-1]
    assert reordered["canUndo"] is True
    assert reordered["canRedo"] is False
    undone = backend.execute("review.undo", {"reviewId": reordered["reviewId"]})
    assert [track["id"] for track in undone["tracks"]] == original
    assert undone["reviewId"] not in {result["reviewId"], reordered["reviewId"]}
    assert undone["canUndo"] is False
    assert undone["canRedo"] is True
    redone = backend.execute("review.redo", {"reviewId": undone["reviewId"]})
    assert [track["id"] for track in redone["tracks"]] == original[::-1]
    assert len({result["reviewId"], reordered["reviewId"], undone["reviewId"], redone["reviewId"]}) == 4
    assert redone["canUndo"] is True
    assert redone["canRedo"] is False
    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save", {"reviewId": undone["reviewId"], "name": "Anterior"})
    assert error.value.code == "stale_review"
    saved = backend.execute("playlist.save", {"reviewId": redone["reviewId"], "name": "Rehecho"})
    with pytest.raises(BackendError) as error:
        backend.execute("review.redo", {"reviewId": redone["reviewId"]})
    assert error.value.code == "nothing_to_undo"
    # Opening the saved playlist replaces the list in progress, so its order is read last.
    assert [track["id"] for track in backend.execute("playlist.open", {"playlistId": saved["id"]})["tracks"]] == (
        original[::-1]
    )


def test_nothing_to_undo_or_redo_fails_closed_without_changing_the_review(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    for method in ("review.undo", "review.redo"):
        with pytest.raises(BackendError) as error:
            backend.execute(method, {"reviewId": result["reviewId"]})
        assert error.value.code == "nothing_to_undo"
    assert backend.review_id == result["reviewId"]
    assert backend.execute("review.details", {"reviewId": result["reviewId"]})["reviewId"] == result["reviewId"]
    for params in ({}, {"reviewId": result["reviewId"], "trackId": "a" * 64}, {"reviewId": "not-a-review"}):
        with pytest.raises(BackendError) as error:
            backend.execute("review.undo", params)
        assert error.value.code == "invalid_params"
    assert backend.review_id == result["reviewId"]


def test_undo_keeps_the_revision_and_source_checks_of_any_other_edit(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    edited = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": swapped(result)})
    with pytest.raises(BackendError) as error:
        backend.execute("review.undo", {"reviewId": result["reviewId"]})
    assert error.value.code == "stale_review"
    Path(backend.review.recommendation.ordered_tracks[0].path).write_bytes(b"changed after the edit")
    with pytest.raises(BackendError) as error:
        backend.execute("review.undo", {"reviewId": edited["reviewId"]})
    assert error.value.code == "stale_review"
    with pytest.raises(BackendError) as error:
        backend.execute("review.redo", {"reviewId": edited["reviewId"]})
    assert error.value.code == "stale_review"


def test_history_keeps_at_most_fifty_states(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    current = result
    for step in range(51):
        ids = swapped(current, 0, 1) if step % 2 == 0 else swapped(current, 2, 3)
        current = backend.execute("review.reorder", {"reviewId": current["reviewId"], "trackIds": ids})
    for _ in range(50):
        current = backend.execute("review.undo", {"reviewId": current["reviewId"]})
    assert current["canUndo"] is False
    with pytest.raises(BackendError) as error:
        backend.execute("review.undo", {"reviewId": current["reviewId"]})
    assert error.value.code == "nothing_to_undo"


def test_a_new_edit_clears_the_redo_history(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    edited = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": swapped(result)})
    undone = backend.execute("review.undo", {"reviewId": edited["reviewId"]})
    assert undone["canRedo"] is True
    replaced = backend.execute("review.reorder", {"reviewId": undone["reviewId"], "trackIds": swapped(undone, 0, 1)})
    assert replaced["canRedo"] is False
    with pytest.raises(BackendError) as error:
        backend.execute("review.redo", {"reviewId": replaced["reviewId"]})
    assert error.value.code == "nothing_to_undo"


def test_a_new_generation_starts_an_empty_history(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": swapped(result)})
    selected = backend.execute("prep.select", {"planId": result["planId"], "variant": "safe"})
    assert selected["canUndo"] is False
    assert selected["canRedo"] is False
    with pytest.raises(BackendError) as error:
        backend.execute("review.undo", {"reviewId": selected["reviewId"]})
    assert error.value.code == "nothing_to_undo"


def test_existing_edit_commands_keep_their_contracts(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "requiredTrackIds": [identity(records[0])]})
    ids = [track["id"] for track in result["tracks"]]
    with pytest.raises(BackendError) as error:
        backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": identity(records[0])})
    assert error.value.code == "protected_track"
    with pytest.raises(BackendError) as error:
        backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": ids[:3]})
    assert error.value.code == "invalid_params"
    comparison = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": ids[1]})
    assert comparison["reviewId"] == result["reviewId"]
    assert set(comparison) == {"reviewId", "replacement", "available", "original", "proposed", "message"}
    details = backend.execute("review.details", {"reviewId": result["reviewId"]})
    assert {"transitions", "readinessChecks", "readinessSummary", "engineFacts"} <= set(details)
    assert backend.review_id == result["reviewId"]


def test_undo_refuses_to_restore_a_track_that_changed_since_its_removal(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    target = result["tracks"][1]["id"]
    removed_path = next(record.path for record in records if identity(record) == target)
    edited = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": target})
    Path(removed_path).write_bytes(b"changed after removal")
    with pytest.raises(BackendError) as error:
        backend.execute("review.undo", {"reviewId": edited["reviewId"]})
    assert error.value.code == "stale_review"
    assert backend.review_id == edited["reviewId"]
