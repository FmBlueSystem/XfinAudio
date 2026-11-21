"""Fit the generated list to a release-year period in one undoable edit (S13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from tests.test_review_extend import stored_backend
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError, _public_track
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import (
    PlaylistRecommendation,
    recommend_playlist,
    recommendation_fitted,
    recommendation_reordered,
)
from xfinaudio.recommendation.scoring import TransitionScoringConfig, score_transition


def built(tmp_path: Path, specs: list[tuple[str, float, int | None]]) -> tuple[HeadlessBackend, list[TrackRecord]]:
    """A library of one track per ``(Camelot key, BPM, release year)``, in order."""
    root = tmp_path / "music"
    root.mkdir()
    records = [
        TrackRecord(
            path=str(root / f"{index:03}.flac"),
            title=f"Track {index}",
            artist="Artist",
            bpm=bpm,
            camelot_key=key,
            energy_level=5,
            duration=240,
            genre="House",
            metadata_status="complete",
            release_year=year,
        )
        for index, (key, bpm, year) in enumerate(specs)
    ]
    for record in records:
        Path(record.path).touch()
    backend = HeadlessBackend(tmp_path / "data")
    backend.roots = [root]
    backend.repository.save_scan_results(records)
    return backend, records


def aged(tmp_path: Path, years: list[int | None]) -> tuple[HeadlessBackend, list[TrackRecord]]:
    """A library of one interchangeable track per release year."""
    return built(tmp_path, [("8A", 120.0, year) for year in years])


def generated(backend: HeadlessBackend, count: int = 4, **intent: object) -> dict:
    return backend.execute("prep.generate", {"targetTrackCount": count, **intent})


def fitted(backend: HeadlessBackend, result: dict, year_min: object, year_max: object) -> dict:
    return backend.execute(
        "review.fit_period", {"reviewId": result["reviewId"], "yearMin": year_min, "yearMax": year_max}
    )


def details(backend: HeadlessBackend, result: dict) -> dict:
    return backend.execute("review.details", {"reviewId": result["reviewId"]})


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def titles(result: dict) -> list[str]:
    return [track["title"] for track in result["tracks"]]


def listed_paths(backend: HeadlessBackend) -> set[str]:
    assert backend.review is not None
    return {track.path for track in backend.review.recommendation.ordered_tracks}


def years(backend: HeadlessBackend) -> list[int | None]:
    assert backend.review is not None
    return [track.release_year for track in backend.review.recommendation.ordered_tracks]


def reaged(backend: HeadlessBackend, records: list[TrackRecord], year_of) -> None:
    """Give the library its release years without touching the files themselves."""
    backend.repository.save_scan_results(
        [record.model_copy(update={"release_year": year_of(record)}) for record in records]
    )


def test_fit_period_replaces_every_out_of_period_track_in_place_and_is_one_undo_step(tmp_path: Path) -> None:
    backend, records = aged(tmp_path, [None] * 10)
    # Generation ignores the release year, so the list a second run picks is the one the
    # first run picked: the years can be assigned between the two runs.
    first = generated(backend)
    held = listed_paths(backend)
    reaged(backend, records, lambda record: 2000 if record.path in held else 1985)
    result = generated(backend)
    assert ids(result) == ids(first)
    original = ids(result)
    assert years(backend) == [2000] * 4
    fit = fitted(backend, result, 1980, 1989)
    assert fit["reviewId"] != result["reviewId"]
    assert len(ids(fit)) == 4
    # Every position was replaced by a library track from the period, in place.
    assert set(ids(fit)).isdisjoint(original)
    assert years(backend) == [1985] * 4
    assert fit["period"] == {"yearMin": 1980, "yearMax": 1989, "replaced": 4, "kept": []}
    assert (fit["canUndo"], fit["canRedo"]) == (True, False)
    # The answer is the usual review payload plus the period report, and it is the live review.
    assert details(backend, fit) == {key: value for key, value in fit.items() if key != "period"}
    assert fit["transitionScores"] == [score.total_score for score in backend.review.recommendation.transition_scores]
    # The whole run is one undo step, and the fitted list is one redo away.
    undone = backend.execute("review.undo", {"reviewId": fit["reviewId"]})
    assert ids(undone) == original
    assert years(backend) == [2000] * 4
    assert undone["canRedo"] is True
    assert ids(backend.execute("review.redo", {"reviewId": undone["reviewId"]})) == ids(fit)


def test_a_protected_opening_outside_the_period_is_kept_and_reported(tmp_path: Path) -> None:
    backend, records = aged(tmp_path, [None] * 8)
    first = generated(backend)
    opening = first["tracks"][0]["id"]
    held = listed_paths(backend)
    rest = [record for record in records if record.path not in held]
    # Only two library tracks come from 1985, so one out-of-period slot has nowhere to go.
    from_1985 = {record.path for record in rest[:2]}

    def year_of(record: TrackRecord) -> int:
        if record.path in held:
            return 2023 if _public_track(record)["id"] == opening else 2000
        return 1985 if record.path in from_1985 else 1995

    reaged(backend, records, year_of)
    result = generated(backend, startTrackId=opening)
    assert ids(result) == ids(first)
    assert years(backend) == [2023, 2000, 2000, 2000]
    fit = fitted(backend, result, 1980, 1989)
    assert fit["period"] == {
        "yearMin": 1980,
        "yearMax": 1989,
        "replaced": 2,
        "kept": [
            {"position": 1, "title": first["tracks"][0]["title"], "year": 2023, "reason": "protected"},
            {"position": 4, "title": first["tracks"][3]["title"], "year": 2000, "reason": "no_candidate"},
        ],
    }
    assert ids(fit)[0] == opening
    assert years(backend)[0] == 2023


def test_an_unknown_year_is_outside_the_period_and_reported_with_a_null_year(tmp_path: Path) -> None:
    backend, records = aged(tmp_path, [None] * 8)
    first = generated(backend)
    opening = first["tracks"][0]["id"]
    held = listed_paths(backend)
    rest = [record for record in records if record.path not in held]
    from_1985 = {record.path for record in rest[:2]}

    def year_of(record: TrackRecord) -> int | None:
        if record.path in held:
            return None if _public_track(record)["id"] == opening else 2000
        return 1985 if record.path in from_1985 else 1995

    reaged(backend, records, year_of)
    result = generated(backend, startTrackId=opening)
    assert ids(result) == ids(first)
    fit = fitted(backend, result, 1980, 1989)
    assert fit["period"]["replaced"] == 2
    assert fit["period"]["kept"] == [
        {"position": 1, "title": first["tracks"][0]["title"], "year": None, "reason": "protected"},
        {"position": 4, "title": first["tracks"][3]["title"], "year": 2000, "reason": "no_candidate"},
    ]
    assert years(backend)[0] is None


def test_a_list_already_inside_the_period_fails_with_no_candidates_and_changes_nothing(tmp_path: Path) -> None:
    backend, _ = aged(tmp_path, [1985] * 6)
    result = generated(backend)
    before = (backend.review, backend.review_id, list(backend.review_actions.history))
    with pytest.raises(BackendError) as error:
        fitted(backend, result, 1980, 1989)
    assert error.value.code == "no_candidates"
    assert (backend.review, backend.review_id, list(backend.review_actions.history)) == before
    assert details(backend, result)["canUndo"] is False


def test_the_removed_set_keeps_an_in_period_candidate_out(tmp_path: Path) -> None:
    backend, records = aged(tmp_path, [2000, 2000, 1985, 2001])
    result = generated(backend)
    assert len(ids(result)) == 4
    # The only track from 1985 leaves the list, and a track of the removed set never
    # comes back: the rest of the list has nowhere to go.
    after = backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": identity(records[2])})
    before = (backend.review, backend.review_id)
    with pytest.raises(BackendError) as error:
        fitted(backend, after, 1980, 1989)
    assert error.value.code == "no_candidates"
    assert (backend.review, backend.review_id) == before


def test_refused_periods_change_nothing(tmp_path: Path) -> None:
    backend, _ = aged(tmp_path, [1980 + index for index in range(8)])
    result = generated(backend)
    before = (backend.review, backend.review_id, list(backend.review_actions.history))
    refused = [(1899, 1990), (1980, 2101), (1990, 1980), (True, 1990), ("1980", 1980), (1980, 1980.0), (None, 1980)]
    for year_min, year_max in refused:
        with pytest.raises(BackendError) as error:
            fitted(backend, result, year_min, year_max)
        assert error.value.code == "invalid_params"
    for params in (
        {"reviewId": result["reviewId"], "yearMin": 1980},
        {"reviewId": result["reviewId"], "yearMin": 1980, "yearMax": 1989, "genre": "House"},
        {"yearMin": 1980, "yearMax": 1989},
    ):
        with pytest.raises(BackendError) as error:
            backend.execute("review.fit_period", params)
        assert error.value.code == "invalid_params"
    with pytest.raises(BackendError) as error:
        backend.execute("review.fit_period", {"reviewId": "0" * 36, "yearMin": 1980, "yearMax": 1989})
    assert error.value.code in {"invalid_params", "stale_review"}
    assert (backend.review, backend.review_id, list(backend.review_actions.history)) == before


@pytest.mark.parametrize("changed", ["candidate", "listed"])
def test_a_track_changed_on_disk_refuses_the_fit_and_changes_nothing(tmp_path: Path, changed: str) -> None:
    backend, records = aged(tmp_path, [None] * 8)
    first = generated(backend)
    held = listed_paths(backend)
    reaged(backend, records, lambda record: 2000 if record.path in held else 1985)
    result = generated(backend)
    assert ids(result) == ids(first)
    for record in records:
        if (record.path in held) == (changed == "listed"):
            Path(record.path).write_bytes(b"changed after generation")
    before = (backend.review, backend.review_id, list(backend.review_actions.history))
    with pytest.raises(BackendError) as error:
        fitted(backend, result, 1980, 1989)
    assert error.value.code == "stale_review"
    assert (backend.review, backend.review_id, list(backend.review_actions.history)) == before


def test_the_genre_filter_of_the_variant_is_used_before_the_rest_of_the_library(tmp_path: Path) -> None:
    backend, records = aged(tmp_path, [None] * 6)
    backend.repository.save_scan_results(
        [
            record.model_copy(update={"genre": "House" if index < 3 else "Techno"})
            for index, record in enumerate(records)
        ]
    )
    first = generated(backend, 2, genreFocus="House")
    held = listed_paths(backend)
    in_period_genre = next(record for record in records if record.path not in held)
    reaged(backend, records, lambda record: 2000 if record.path in held else 1985)
    # The one in-genre candidate is taken first and the rest of the library fills the other slot.
    result = generated(backend, 2, genreFocus="House")
    assert ids(result) == ids(first)
    fit = fitted(backend, result, 1980, 1989)
    entered = set(ids(fit))
    assert fit["period"] == {"yearMin": 1980, "yearMax": 1989, "replaced": 2, "kept": []}
    assert identity(in_period_genre) in entered
    assert len(entered - {identity(in_period_genre)}) == 1


def test_a_restart_recovers_the_fitted_list_and_refits_nothing(tmp_path: Path) -> None:
    backend, records = aged(tmp_path, [None] * 10)
    generated(backend)
    held = listed_paths(backend)
    reaged(backend, records, lambda record: 2000 if record.path in held else 1985)
    result = generated(backend)
    fit = fitted(backend, result, 1980, 1989)
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert (resumed["available"], resumed["dropped"]) == (True, False)
    assert ids(resumed["review"]) == ids(fit)
    assert (resumed["review"]["canUndo"], resumed["review"]["canRedo"]) == (False, False)
    with pytest.raises(BackendError) as error:
        fitted(restarted, fit, 1980, 1989)
    assert error.value.code == "no_candidates"


def test_a_review_without_a_current_revision_is_stale(tmp_path: Path) -> None:
    backend, _ = aged(tmp_path, [1980 + index for index in range(6)])
    previous = generated(backend)
    current = generated(backend, name="Otro set")
    with pytest.raises(BackendError) as error:
        fitted(backend, previous, 1980, 1984)
    assert error.value.code == "stale_review"
    assert backend.review_id == current["reviewId"]


def test_a_library_without_a_single_year_fails_with_no_candidates(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path, 6)
    result = generated(backend)
    with pytest.raises(BackendError) as error:
        fitted(backend, result, 1980, 1989)
    assert error.value.code == "no_candidates"


def engine_track(path: str, *, key: str, bpm: float = 120.0, year: int | None = None) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=Path(path).stem,
        artist="Artist",
        bpm=bpm,
        camelot_key=key,
        energy_level=5,
        genre="House",
        duration=240,
        metadata_status="complete",
        release_year=year,
    )


def pinned(*tracks: TrackRecord) -> PlaylistRecommendation:
    """A generated list pinned to *tracks*' order, so its scores describe that order."""
    return recommendation_reordered(recommend_playlist(list(tracks), "build"), [track.path for track in tracks])


def test_each_position_takes_the_candidate_whose_weakest_transition_is_highest() -> None:
    """The second slot is priced against the track that just entered, not against the one it replaced."""
    opening = engine_track("/opening.flac", key="8A")
    middle = engine_track("/middle.flac", key="10A")
    closing = engine_track("/closing.flac", key="8A")
    recommendation = pinned(opening, middle, closing)
    config = TransitionScoringConfig(weights=recommendation.strategy.weights)

    def score(left: TrackRecord, right: TrackRecord) -> float:
        return score_transition(left, right, weights=config.weights, config=config).total_score

    entry = engine_track("/entry.flac", key="10A", year=1985)
    near = engine_track("/near.flac", key="8A", year=1985)
    clash = engine_track("/clash.flac", key="9A", year=1985)
    weak = engine_track("/weak.flac", key="5A", year=1985)
    candidates = [entry, near, clash, weak]
    # The first slot answers to the middle track only, so the 10A entry wins it. The second
    # slot is then priced between that entry and the closing track -- and the two oracles
    # disagree, which is what makes the entered track's role observable.
    after_entering = {item.path: min(score(entry, item), score(item, closing)) for item in (near, clash, weak)}
    after_original = {item.path: min(score(opening, item), score(item, closing)) for item in (near, clash, weak)}
    assert max(after_entering, key=lambda path: after_entering[path]) != max(
        after_original, key=lambda path: after_original[path]
    )

    fitted_recommendation = recommendation_fitted(recommendation, candidates, 1980, 1989)

    assert [track.path for track in fitted_recommendation.ordered_tracks] == [
        "/entry.flac",
        "/clash.flac",
        "/near.flac",
    ]
    assert fitted_recommendation.total_score == sum(
        transition.total_score for transition in fitted_recommendation.transition_scores
    )
