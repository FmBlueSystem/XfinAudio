"""Grow the generated review toward its requested length (S1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.library.duplicate_grouping import playlist_duplicate_group_key


def generated(tmp_path: Path, count: int = 10) -> tuple[HeadlessBackend, list, dict]:
    backend, records = seeded(tmp_path, count)
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": 4})


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def extended(backend: HeadlessBackend, result: dict, target: int) -> dict:
    return backend.execute("review.extend", {"reviewId": result["reviewId"], "targetTrackCount": target})


def stored_backend(backend: HeadlessBackend) -> HeadlessBackend:
    """Restart the core the way the app does: the roots are the ones a scan authorized."""
    (backend.data_dir / "roots.json").write_text(json.dumps([str(root) for root in backend.roots]), encoding="utf-8")
    return HeadlessBackend(backend.data_dir)


def test_extend_reaches_the_target_reports_its_growth_and_is_one_undo_step(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    original = ids(result)
    grew = extended(backend, result, 6)
    grown = ids(grew)
    assert len(grown) == 6
    assert set(original) <= set(grown)
    assert grew["extended"] == {"requested": 2, "added": 2, "outsideGenre": 0}
    assert grew["reviewId"] != result["reviewId"]
    assert (grew["canUndo"], grew["canRedo"]) == (True, False)
    # The answer is the usual review payload plus the growth report, and it is the live review.
    details = backend.execute("review.details", {"reviewId": grew["reviewId"]})
    assert details == {key: value for key, value in grew.items() if key != "extended"}
    scores = backend.review.recommendation.transition_scores
    assert grew["transitionScores"] == [score.total_score for score in scores]
    assert len(scores) == 5
    undone = backend.execute("review.undo", {"reviewId": grew["reviewId"]})
    assert ids(undone) == original
    assert undone["reviewId"] not in {result["reviewId"], grew["reviewId"]}
    assert (undone["canUndo"], undone["canRedo"]) == (False, True)
    assert ids(backend.execute("review.redo", {"reviewId": undone["reviewId"]})) == grown


def test_the_new_tracks_are_spread_through_the_list_not_appended(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    grew = extended(backend, result, 6)
    added = set(ids(grew)) - set(ids(result))
    assert len(added) == 2
    positions = [index for index, track_id in enumerate(ids(grew)) if track_id in added]
    assert positions != [4, 5]
    assert any(0 < position < len(ids(grew)) - 1 for position in positions)


def test_existing_order_is_kept_and_nothing_goes_before_the_protected_opening(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 10)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "startTrackId": identity(records[0])})
    original = ids(result)
    assert original[0] == identity(records[0])
    grown = ids(extended(backend, result, 7))
    assert len(grown) == 7
    assert grown[0] == identity(records[0])
    assert [track_id for track_id in grown if track_id in original] == original
    assert len(set(grown)) == len(grown)


def test_nothing_goes_after_the_protected_closing_or_inside_the_manual_prefix(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 10)
    result = backend.execute(
        "prep.generate",
        {
            "targetTrackCount": 4,
            "endTrackId": identity(records[2]),
            "requiredTrackIds": [identity(records[1]), identity(records[3])],
        },
    )
    original = ids(result)
    assert original[:2] == [identity(records[1]), identity(records[3])]
    assert original[-1] == identity(records[2])
    grown = ids(extended(backend, result, 7))
    assert len(grown) == 7
    assert grown[:2] == [identity(records[1]), identity(records[3])]
    assert grown[-1] == identity(records[2])
    assert [track_id for track_id in grown if track_id in original] == original


def test_removed_and_excluded_tracks_never_return(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 10)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "excludedTrackIds": [identity(records[9])]})
    dropped = ids(result)[1]
    after_removal = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": dropped})
    assert dropped not in ids(after_removal)
    grown = extended(backend, after_removal, 6)
    assert len(ids(grown)) == 6
    assert dropped not in ids(grown)
    assert identity(records[9]) not in ids(grown)


def test_no_track_is_added_twice_and_no_version_of_a_listed_song_returns(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    sibling = records[0].model_copy(
        update={"path": str(Path(records[0].path).with_name("000 (Edit).flac")), "title": f"{records[0].title} (Edit)"}
    )
    Path(sibling.path).touch()
    backend.repository.save_scan_results([*records, sibling])
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    # The library holds nine files but only eight distinct songs, so nine is out of reach.
    grew = extended(backend, result, 9)
    grown = ids(grew)
    assert grew["extended"] == {"requested": 5, "added": 4, "outsideGenre": 0}
    assert len(grown) == 8
    assert len(set(grown)) == len(grown)
    by_id = {track["id"]: track for track in grew["tracks"]}
    keys = [playlist_duplicate_group_key(by_id[track_id]["title"], by_id[track_id]["artist"]) for track_id in grown]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("target", [6, 8])
def test_the_genre_filter_is_used_first_and_the_rest_of_the_library_after_it(tmp_path: Path, target: int) -> None:
    backend, records = seeded(tmp_path, 12)
    focused = [record.model_copy(update={"genre": "House"}) for record in records[:6]]
    rest = [record.model_copy(update={"genre": "Techno"}) for record in records[6:]]
    backend.repository.save_scan_results([*focused, *rest])
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "genreFocus": "House"})
    assert {track["genre"] for track in result["tracks"]} == {"House"}
    grew = extended(backend, result, target)
    added = [track for track in grew["tracks"] if track["id"] not in ids(result)]
    outside = [track for track in added if track["genre"] != "House"]
    assert grew["extended"] == {"requested": target - 4, "added": target - 4, "outsideGenre": len(outside)}
    assert len(ids(grew)) == target
    if target == 6:
        assert outside == []
    else:
        assert len(outside) == 2


def test_refused_extensions_change_nothing(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path, 8)
    original = ids(result)
    before = backend.review, backend.review_id
    for target in (4, 3, 0, 101, 10**3, True, "6", 6.0, None, [6]):
        with pytest.raises(BackendError) as error:
            backend.execute("review.extend", {"reviewId": result["reviewId"], "targetTrackCount": target})
        assert error.value.code == "invalid_params"
    for params in (
        {"reviewId": result["reviewId"]},
        {"reviewId": result["reviewId"], "targetTrackCount": 6, "path": "/private/track.flac"},
        {"targetTrackCount": 6},
    ):
        with pytest.raises(BackendError) as error:
            backend.execute("review.extend", params)
        assert error.value.code == "invalid_params"
    with pytest.raises(BackendError) as error:
        backend.execute("review.extend", {"reviewId": "0" * 36, "targetTrackCount": 6})
    assert error.value.code in {"invalid_params", "stale_review"}
    assert backend.review is before[0]
    assert backend.review_id == result["reviewId"]
    assert ids(backend.execute("review.details", {"reviewId": result["reviewId"]})) == original


def test_an_exhausted_library_fails_with_no_candidates_and_changes_nothing(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path, 4)
    original = ids(result)
    before = backend.review, backend.review_id
    with pytest.raises(BackendError) as error:
        extended(backend, result, 5)
    assert error.value.code == "no_candidates"
    assert backend.review is before[0]
    assert backend.review_id == result["reviewId"]
    assert ids(backend.execute("review.details", {"reviewId": result["reviewId"]})) == original


def test_the_shortfall_warning_follows_the_new_length(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 12)
    focused = [record.model_copy(update={"genre": "House"}) for record in records[:6]]
    rest = [record.model_copy(update={"genre": "Techno"}) for record in records[6:]]
    backend.repository.save_scan_results([*focused, *rest])
    result = backend.execute("prep.generate", {"targetTrackCount": 8, "genreFocus": "House"})
    shortfall = "Track count shortfall: selected 6 of 8 requested tracks"
    assert shortfall in result["warnings"]
    assert backend.review.recommendation.warnings.count(shortfall) == 1
    to_seven = extended(backend, result, 7)
    assert to_seven["extended"] == {"requested": 1, "added": 1, "outsideGenre": 1}
    assert "Track count shortfall: selected 7 of 8 requested tracks" in to_seven["warnings"]
    assert shortfall not in to_seven["warnings"]
    assert to_seven["warnings"].count("Track count shortfall: selected 7 of 8 requested tracks") == 1
    assert backend.review.recommendation.warnings.count("Track count shortfall: selected 7 of 8 requested tracks") == 1
    to_eight = extended(backend, to_seven, 8)
    assert to_eight["extended"] == {"requested": 1, "added": 1, "outsideGenre": 1}
    assert not any("Track count shortfall" in warning for warning in to_eight["warnings"])
    assert not any("Track count shortfall" in warning for warning in backend.review.recommendation.warnings)


def test_a_restart_recovers_the_grown_list(tmp_path: Path) -> None:
    backend, _, result = generated(tmp_path)
    grew = extended(backend, result, 6)
    grown = ids(grew)
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert (resumed["available"], resumed["dropped"]) == (True, False)
    assert resumed["review"]["reviewId"] == grew["reviewId"]
    assert ids(resumed["review"]) == grown
    assert (resumed["review"]["canUndo"], resumed["review"]["canRedo"]) == (False, False)
    assert str(tmp_path) not in json.dumps(resumed)
    again = restarted.execute("review.extend", {"reviewId": grew["reviewId"], "targetTrackCount": 7})
    assert len(ids(again)) == 7
    assert set(grown) <= set(ids(again))
