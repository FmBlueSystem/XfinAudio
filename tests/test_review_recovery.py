"""Recover the active generated review after a restart (S6)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.review_store import FIELDS, store_path


def stored_backend(backend: HeadlessBackend) -> HeadlessBackend:
    """Restart the core the way the app does: the roots are the ones a scan authorized."""
    (backend.data_dir / "roots.json").write_text(json.dumps([str(root) for root in backend.roots]), encoding="utf-8")
    return HeadlessBackend(backend.data_dir)


def generated(tmp_path: Path, count: int = 8) -> tuple[HeadlessBackend, Any, dict]:
    backend, records = seeded(tmp_path, count)
    required = [identity(records[0])]
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": 4, "requiredTrackIds": required})


def swapped(result: dict, first: int = -2, second: int = -1) -> list[str]:
    ids = [track["id"] for track in result["tracks"]]
    ids[first], ids[second] = ids[second], ids[first]
    return ids


def removed_track(result: dict) -> str:
    return next(track["id"] for track in result["tracks"] if track["id"] not in result["protectedTrackIds"])


def edited_review(backend: HeadlessBackend, result: dict) -> dict:
    reordered = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": swapped(result)})
    return backend.execute("review.remove", {"reviewId": reordered["reviewId"], "trackId": removed_track(reordered)})


def test_an_edited_review_roundtrips_a_restart_faithfully(tmp_path: Path) -> None:
    backend, records, result = generated(tmp_path)
    required = identity(records[0])
    assert required in result["protectedTrackIds"]
    current = edited_review(backend, result)
    before = backend.execute("review.details", {"reviewId": current["reviewId"]})
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert resumed["available"] is True
    assert resumed["dropped"] is False
    restored = resumed["review"]
    assert restored["reviewId"] == current["reviewId"]
    assert restored["planId"] == current["planId"]
    assert [track["id"] for track in restored["tracks"]] == [track["id"] for track in current["tracks"]]
    assert {key: value for key, value in restored.items() if key not in ("canUndo", "canRedo")} == {
        key: value for key, value in before.items() if key not in ("canUndo", "canRedo")
    }
    # Any restore names the same opaque tracks it keeps, and never the files behind them.
    assert str(tmp_path) not in json.dumps(resumed)
    assert restored["canUndo"] is False and restored["canRedo"] is False
    # The restored review is the live one: every edit keeps working under its identity.
    assert restarted.execute("review.details", {"reviewId": current["reviewId"]})["reviewId"] == current["reviewId"]
    continues = restarted.execute("review.reorder", {"reviewId": current["reviewId"], "trackIds": swapped(restored)})
    assert continues["reviewId"] != current["reviewId"]
    comparison = restarted.execute(
        "review.compare", {"reviewId": continues["reviewId"], "trackId": removed_track(continues)}
    )
    assert comparison["available"] is True
    offered = comparison["replacement"]["id"]
    replaced = restarted.execute(
        "review.replace",
        {"reviewId": continues["reviewId"], "trackId": removed_track(continues), "replacementId": offered},
    )
    assert len(replaced["tracks"]) == len(continues["tracks"])
    protected = replaced["protectedTrackIds"]
    assert required in protected
    for track_id in protected:
        with pytest.raises(BackendError) as error:
            restarted.execute("review.remove", {"reviewId": replaced["reviewId"], "trackId": track_id})
        assert error.value.code == "protected_track"
    undone = restarted.execute("review.undo", {"reviewId": replaced["reviewId"]})
    assert [track["id"] for track in undone["tracks"]] == [track["id"] for track in continues["tracks"]]
    assert offered not in [track["id"] for track in undone["tracks"]]
    # The restored review began with no history of its own: two edits, two undos, then nothing.
    back = restarted.execute("review.undo", {"reviewId": undone["reviewId"]})
    assert [track["id"] for track in back["tracks"]] == [track["id"] for track in restored["tracks"]]
    with pytest.raises(BackendError) as error:
        restarted.execute("review.undo", {"reviewId": back["reviewId"]})
    assert error.value.code == "nothing_to_undo"


def test_the_stored_file_keeps_its_contract_and_a_restart_answers_the_same_facts(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    current = edited_review(backend, result)
    before = backend.execute("review.details", {"reviewId": current["reviewId"]})
    stored = json.loads(store_path(backend.data_dir).read_text(encoding="utf-8"))
    # The two new payload facts are additive: the recovery contract stores exactly what it did before.
    assert set(stored) == set(FIELDS)
    restarted = stored_backend(backend)
    restored = restarted.execute("review.resume", {})["review"]
    assert restored["transitionScores"] == before["transitionScores"]
    assert restored["readinessChecks"] == before["readinessChecks"]
    assert len(restored["transitionScores"]) == len(restored["tracks"]) - 1


def test_the_removed_set_survives_so_a_banned_track_is_not_backfilled(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 6)
    # Two out-of-band candidates can never backfill a 120 BPM slot, so a removal
    # shortens the set and the only possible backfill would be the removed track.
    outlier = {"bpm": 175, "camelot_key": "2B", "energy_level": 9}
    backend.repository.save_scan_results([*records[:4], *(record.model_copy(update=outlier) for record in records[4:])])
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    original = [track["id"] for track in result["tracks"]]
    assert len(original) == 4
    shortened = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": original[0]})
    assert [track["id"] for track in shortened["tracks"]] == original[1:]
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})["review"]
    assert [track["id"] for track in resumed["tracks"]] == original[1:]
    again = restarted.execute("review.remove", {"reviewId": resumed["reviewId"], "trackId": original[1]})
    assert [track["id"] for track in again["tracks"]] == original[2:]
    assert original[0] not in [track["id"] for track in again["tracks"]]


def test_a_changed_library_drops_the_stored_review_with_an_explicit_notice(tmp_path: Path) -> None:
    backend, records, _ = generated(tmp_path)
    backend.repository.save_scan_results([records[0].model_copy(update={"bpm": 126}), *records[1:]])
    restarted = stored_backend(backend)
    assert restarted.execute("review.resume", {}) == {"available": False, "review": None, "dropped": True}
    with pytest.raises(BackendError) as error:
        restarted.execute("review.details", {"reviewId": "a" * 8})
    assert error.value.code == "invalid_params"
    # The drop is final: a later start has nothing left to report.
    restarted_backend = stored_backend(restarted)
    assert restarted_backend.execute("review.resume", {}) == {"available": False, "review": None, "dropped": False}


@pytest.mark.parametrize(
    "content",
    [
        "{broken",
        "[]",
        json.dumps({"version": 2, "reviewId": "x"}),
        json.dumps({"version": 1}),
        json.dumps(
            {
                "version": 1,
                "reviewId": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                "planId": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
                "name": "Set",
                "variant": "balanced",
                "warnings": [],
                "variants": [],
                "review": {"recommendation": {"ordered_tracks": "/Users/private"}},
                "plan": {},
                "removed": ["/Users/private/track.flac"],
                "extra": True,
            }
        ),
        json.dumps(
            {
                "version": 1,
                "reviewId": "/Users/private/review",
                "planId": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
                "name": "Set",
                "variant": "balanced",
                "warnings": [],
                "variants": [],
                "review": {},
                "plan": {},
                "removed": [],
            }
        ),
    ],
)
def test_a_missing_corrupt_or_out_of_contract_file_is_ignored_and_logged(
    tmp_path: Path, content: str, caplog: pytest.LogCaptureFixture
) -> None:
    backend, _ = seeded(tmp_path)
    (backend.data_dir / "active_review.json").write_text(content, encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        restarted = stored_backend(backend)
    assert caplog.records, "a corrupt or out-of-contract file must leave a warning"
    assert restarted.execute("review.resume", {}) == {"available": False, "review": None, "dropped": False}
    assert restarted.execute("prep.generate", {"targetTrackCount": 3})["tracks"]


def test_a_storage_failure_never_fails_the_edit(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    backend, _, result = generated(tmp_path)
    (backend.data_dir / "active_review.json.tmp").mkdir()
    with caplog.at_level(logging.WARNING):
        edited = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": removed_track(result)})
    assert edited["reviewId"] != result["reviewId"]
    assert caplog.records, "a refused store write must leave a warning"


def test_a_new_generation_replaces_the_file_and_saving_a_playlist_keeps_it(tmp_path: Path) -> None:
    backend, _, first = generated(tmp_path)
    saved = backend.execute("playlist.save", {"name": "Kept", "reviewId": first["reviewId"]})
    assert saved["trackCount"] == len(first["tracks"])
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert resumed["available"] is True
    assert resumed["review"]["reviewId"] == first["reviewId"]
    second = restarted.execute("prep.generate", {"targetTrackCount": 4})
    assert second["reviewId"] != first["reviewId"]
    after = stored_backend(restarted).execute("review.resume", {})
    assert after["available"] is True
    assert after["review"]["reviewId"] == second["reviewId"]


def test_resume_with_nothing_stored_and_refuses_extra_fields(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    assert backend.execute("review.resume", {}) == {"available": False, "review": None, "dropped": False}
    for params in ({"reviewId": "a" * 8}, {"path": "/Users/private"}, {"reviewId": "a" * 64}):
        with pytest.raises(BackendError) as error:
            backend.execute("review.resume", params)
        assert error.value.code == "invalid_params"


def test_a_discarded_review_is_never_restored(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    backend.invalidate_review()
    assert backend.review is None
    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save", {"name": "Stale", "reviewId": result["reviewId"]})
    assert error.value.code == "stale_review"
    restarted = stored_backend(backend)
    assert restarted.execute("review.resume", {}) == {"available": False, "review": None, "dropped": False}
