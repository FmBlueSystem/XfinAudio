"""Grow the generated review toward its requested length (S1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.library.duplicate_grouping import playlist_duplicate_group_key
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    recommend_playlist,
    recommendation_extended,
    recommendation_reordered,
)
from xfinaudio.recommendation.scoring import TransitionScoringConfig, score_transition


def generated(tmp_path: Path, count: int = 10) -> tuple[HeadlessBackend, list, dict]:
    backend, records = seeded(tmp_path, count)
    return backend, records, backend.execute("prep.generate", {"targetTrackCount": 4})


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def extended(backend: HeadlessBackend, result: dict, target: int) -> dict:
    return backend.execute("review.extend", {"reviewId": result["reviewId"], "targetTrackCount": target})


def engine_track(
    path: str,
    *,
    bpm: float,
    key: str,
    energy: int,
    title: str | None = None,
    artist: str = "Artist",
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title if title is not None else Path(path).stem,
        artist=artist,
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        genre="House",
        tags=["Peak"],
        metadata_status="complete",
        duration=240,
    )


def pinned(*tracks: TrackRecord) -> PlaylistRecommendation:
    """A generated list pinned to *tracks*' order, so its scores describe that order."""
    return recommendation_reordered(recommend_playlist(list(tracks), "build"), [track.path for track in tracks])


def scored(recommendation: PlaylistRecommendation, left: TrackRecord, right: TrackRecord) -> float:
    """The transition score the engine would price for *left* into *right*."""
    config = TransitionScoringConfig(weights=recommendation.strategy.weights)
    return score_transition(left, right, weights=config.weights, config=config).total_score


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


def test_a_good_opening_transition_is_kept_because_the_best_pair_wins() -> None:
    """Taking the pool in order broke a good transition for a worse one.

    The first candidate mixes well with the opening but badly with the track
    after it, so the pair it would form between them is the set's weakest while
    its summed score there is the highest it can reach. The second candidate
    fits the end of the list far better than anything the first can offer, so
    the best pair is the tail one and the opening transition must survive.
    """
    opening = engine_track("/opening.flac", bpm=120.0, key="8A", energy=5)
    middle = engine_track("/middle.flac", bpm=121.0, key="9A", energy=6)
    closing = engine_track("/closing.flac", bpm=122.0, key="10A", energy=7)
    recommendation = pinned(opening, middle, closing)
    good = recommendation.transition_scores[0].total_score
    assert good > 0.85
    opener = engine_track("/opener.flac", bpm=118.0, key="7B", energy=5)
    tail = engine_track("/tail.flac", bpm=121.0, key="10A", energy=7)

    grown, outside_genre = recommendation_extended(recommendation, [opener, tail], 4)

    paths = [track.path for track in grown.ordered_tracks]
    assert paths == ["/opening.flac", "/middle.flac", "/closing.flac", "/tail.flac"]
    assert outside_genre == 0
    # The opening transition is untouched: neither replaced nor reordered.
    assert grown.transition_scores[0].total_score == good
    assert (grown.transition_scores[0].left_path, grown.transition_scores[0].right_path) == (
        "/opening.flac",
        "/middle.flac",
    )
    # And the chosen pair is the best one the pool offers, by weakest new transition.
    pairs = {
        ("opener", "start"): scored(recommendation, opener, opening),
        ("opener", "opening-middle"): min(
            scored(recommendation, opening, opener), scored(recommendation, opener, middle)
        ),
        ("tail", "middle-closing"): min(scored(recommendation, middle, tail), scored(recommendation, tail, closing)),
        ("tail", "end"): scored(recommendation, closing, tail),
    }
    assert pairs[("tail", "end")] == max(pairs.values())
    # Priced into the opening gap, the first candidate would replace that good
    # transition with a weaker pair of its own.
    assert pairs[("opener", "opening-middle")] < good


def test_a_tie_on_the_weakest_new_transition_goes_to_the_better_score_sum() -> None:
    """Two pairs tie on their weakest new transition, so the sum has to decide."""
    opening = engine_track("/opening.flac", bpm=120.0, key="8A", energy=5)
    middle = engine_track("/middle.flac", bpm=121.0, key="9A", energy=6)
    closing = engine_track("/closing.flac", bpm=118.0, key="1A", energy=4)
    recommendation = pinned(opening, middle, closing)
    # Both pairs bottom out at the same score: `spread` between the middle and
    # the closing, `tail` after the closing. `spread` adds two transitions and
    # breaks a weak one, so it moves the sum further in the list's favour.
    spread = engine_track("/spread.flac", bpm=121.0, key="11A", energy=4)
    tail = engine_track("/tail.flac", bpm=118.0, key="3A", energy=6)
    assert scored(recommendation, middle, spread) == scored(recommendation, closing, tail)

    grown, _ = recommendation_extended(recommendation, [tail, spread], 4)

    assert [track.path for track in grown.ordered_tracks] == [
        "/opening.flac",
        "/middle.flac",
        "/spread.flac",
        "/closing.flac",
    ]


def test_at_most_the_150_candidates_closest_in_bpm_are_considered() -> None:
    """The stage is bounded by tempo distance, so a crowded library stays cheap."""
    opening = engine_track("/opening.flac", bpm=120.0, key="8A", energy=5)
    middle = engine_track("/middle.flac", bpm=121.0, key="9A", energy=6)
    closing = engine_track("/closing.flac", bpm=122.0, key="10A", energy=7)
    recommendation = pinned(opening, middle, closing)
    # A near-perfect match whose tempo is the farthest from the list: it would
    # win the first step outright, but it is the 151st nearest tempo, so the
    # bounded stage never prices it.
    crowd = [engine_track(f"/crowd{index}.flac", bpm=121.0, key="7B", energy=1) for index in range(150)]
    distant = engine_track("/distant.flac", bpm=123.5, key="8A", energy=5)

    grown, _ = recommendation_extended(recommendation, [distant, *crowd], 4)

    assert [track.path for track in grown.ordered_tracks] == [
        "/crowd0.flac",
        "/opening.flac",
        "/middle.flac",
        "/closing.flac",
    ]


def test_versions_of_a_song_already_in_the_list_are_not_added() -> None:
    """S1: one song joins the list once, whatever its files are called.

    «Funkytown», «Funky Town (Extended Version)» and «Funky Town Vm Short Edit»
    are three files of one song, and the engine's duplicate key reads them as
    three different titles, so the extension owes the list a rule of its own.
    """
    opening = engine_track("/opening.flac", bpm=120.0, key="8A", energy=5)
    listed = engine_track("/listed.flac", bpm=121.0, key="9A", energy=6, title="Funkytown", artist="Lipps Inc")
    recommendation = pinned(opening, listed)
    extended_version = engine_track(
        "/extended.flac", bpm=121.5, key="9A", energy=6, title="Funky Town (Extended Version)", artist="Lipps Inc"
    )
    short_edit = engine_track(
        "/short.flac", bpm=121.0, key="9A", energy=6, title="Funky Town Vm Short Edit", artist="Lipps Inc"
    )
    other = engine_track("/other.flac", bpm=120.5, key="8A", energy=5, title="Another Song", artist="Another Artist")
    # The engine's duplicate key alone would let both versions in.
    versions = (listed, extended_version, short_edit)
    assert len({playlist_duplicate_group_key(track.title, track.artist) for track in versions}) == 3

    grown, outside_genre = recommendation_extended(recommendation, [extended_version, short_edit, other], 3)

    paths = [track.path for track in grown.ordered_tracks]
    assert outside_genre == 0
    assert "/other.flac" in paths
    assert {"/extended.flac", "/short.flac"}.isdisjoint(paths)
    assert len(paths) == 3


@pytest.mark.parametrize(
    ("listed_title", "listed_artist", "version_title", "version_artist"),
    [
        ("She Blinded Me With Science", "Thomas Dolby", "She Blinded Me With Science Short", "Thomas Dolby"),
        ("Love Shack Roam Back Spins By Mark", "The B-52's", "Love Shack / Roam (Back Spins by Mark)", "B52s"),
    ],
)
def test_a_bracketed_or_punctuated_title_that_starts_the_same_names_the_same_song(
    listed_title: str, listed_artist: str, version_title: str, version_artist: str
) -> None:
    """Bracketed text, punctuation and a leading article on the artist do not split a song."""
    opening = engine_track("/opening.flac", bpm=120.0, key="8A", energy=5)
    listed = engine_track("/listed.flac", bpm=121.0, key="9A", energy=6, title=listed_title, artist=listed_artist)
    recommendation = pinned(opening, listed)
    version = engine_track("/version.flac", bpm=121.0, key="9A", energy=6, title=version_title, artist=version_artist)
    other = engine_track("/other.flac", bpm=120.5, key="8A", energy=5, title="Another Song", artist="Another Artist")
    assert playlist_duplicate_group_key(listed_title, listed_artist) != playlist_duplicate_group_key(
        version_title, version_artist
    )

    grown, _ = recommendation_extended(recommendation, [version, other], 3)

    paths = [track.path for track in grown.ordered_tracks]
    assert "/other.flac" in paths
    assert "/version.flac" not in paths


@pytest.mark.parametrize(
    ("listed_title", "listed_artist", "candidate_title", "candidate_artist"),
    [
        # Same title prefix, another act: a cover is not a version.
        ("Funkytown", "Lipps Inc", "Funky Town (Extended Version)", "Someone Else"),
        # Same act, but the shared prefix is shorter than six characters.
        ("Love", "The B-52's", "Love Shack", "The B-52's"),
    ],
)
def test_a_title_prefix_from_another_artist_or_under_six_characters_is_still_added(
    listed_title: str, listed_artist: str, candidate_title: str, candidate_artist: str
) -> None:
    """The same-song rule needs both the same act and at least six shared characters."""
    opening = engine_track("/opening.flac", bpm=120.0, key="8A", energy=5)
    listed = engine_track("/listed.flac", bpm=121.0, key="9A", energy=6, title=listed_title, artist=listed_artist)
    recommendation = pinned(opening, listed)
    candidate = engine_track(
        "/candidate.flac", bpm=121.0, key="9A", energy=6, title=candidate_title, artist=candidate_artist
    )

    grown, _ = recommendation_extended(recommendation, [candidate], 3)

    assert [track.path for track in grown.ordered_tracks] == ["/opening.flac", "/listed.flac", "/candidate.flac"]


def test_a_song_added_by_the_extension_is_not_added_twice_either() -> None:
    """The rule sees the tracks a previous step added, not only the original list."""
    opening = engine_track("/opening.flac", bpm=120.0, key="8A", energy=5)
    closing = engine_track("/closing.flac", bpm=121.0, key="9A", energy=6)
    recommendation = pinned(opening, closing)
    first = engine_track("/first.flac", bpm=121.0, key="9A", energy=6, title="Funkytown", artist="Lipps Inc")
    version = engine_track(
        "/version.flac", bpm=121.0, key="9A", energy=6, title="Funky Town (Extended Version)", artist="Lipps Inc"
    )
    # Both fillers fit far worse than either version, so the song is picked first.
    other_a = engine_track(
        "/other-a.flac", bpm=120.0, key="1A", energy=1, title="Another Song", artist="Another Artist"
    )
    other_b = engine_track("/other-b.flac", bpm=120.0, key="12B", energy=1, title="Third Song", artist="Third Artist")

    grown, _ = recommendation_extended(recommendation, [first, version, other_a, other_b], 4)

    paths = [track.path for track in grown.ordered_tracks]
    assert len(paths) == 4
    assert len([path for path in paths if path in {"/first.flac", "/version.flac"}]) == 1
    assert len(set(paths) & {"/other-a.flac", "/other-b.flac"}) == 1


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
