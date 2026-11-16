"""The list assistant's local library search: eligible tracks only, public fields only.

The search runs on the records the core already stores, so it never reads a file and
never contacts the provider; what leaves this module for the provider carries a short
reference and the DJ-visible fields, never a path and never a track identity.
"""

from __future__ import annotations

import json
import shutil

import pytest
from mutagen.flac import FLAC

from tests.test_headless_ai_context import FIXTURES
from tests.test_headless_ai_context import setup as setup
from xfinaudio.ai.list_chat import SearchQuery
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.library_search import MAX_SEARCH_RESULTS, public_result, search_library


@pytest.fixture
def wide_setup(tmp_path):
    """A library with more eligible tracks than one search is allowed to return."""
    root = tmp_path / "music"
    shutil.copytree(FIXTURES, root)
    for index in range(24):
        copy = root / f"extra-{index:02d}.flac"
        shutil.copyfile(root / "track-5.flac", copy)
        tags = FLAC(copy)
        tags["title"] = f"Extra {index:02d}"
        tags["bpm"] = str(130 + index)
        tags.save()
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Wide review"})
    return backend, root


def listed_paths(backend) -> set[str]:
    assert backend.review is not None
    return {track.path for track in backend.review.recommendation.ordered_tracks}


def anchor_bpms(backend) -> list[float]:
    assert backend.review is not None
    return [track.bpm for track in backend.review.recommendation.ordered_tracks if track.bpm is not None]


def test_a_search_returns_complete_library_tracks_outside_the_list_closest_in_bpm_first(setup):
    backend, _, _ = setup
    listed = listed_paths(backend)
    matches = search_library(backend, [SearchQuery()])
    assert len(matches) == 1
    records = matches[0].records
    assert records
    assert {record.path for record in records}.isdisjoint(listed)
    assert all(record.metadata_status == "complete" for record in records)
    anchors = anchor_bpms(backend)
    distances = [min(abs(bpm - anchor) for anchor in anchors) for record in records if (bpm := record.bpm) is not None]
    assert distances == sorted(distances)
    # The incomplete copy of a listed track is never offered.
    assert all(not record.path.endswith("gap.flac") for record in records)


def test_the_text_matches_the_title_the_artist_and_the_genre(setup):
    backend, _, _ = setup
    by_title = search_library(backend, [SearchQuery(query="test 7")])[0].records
    assert [record.title for record in by_title] == ["Electron test 7"]
    by_artist = search_library(backend, [SearchQuery(query="xfinaudio")])[0].records
    assert len(by_artist) == 4
    by_genre = search_library(backend, [SearchQuery(query="house")])[0].records
    assert len(by_genre) == 4
    assert search_library(backend, [SearchQuery(query="techno")])[0].records == ()


def test_the_genre_bpm_and_key_filters_bound_the_results(setup):
    backend, _, _ = setup
    assert len(search_library(backend, [SearchQuery(genre="House")])[0].records) == 4
    assert search_library(backend, [SearchQuery(genre="Techno")])[0].records == ()
    assert [record.bpm for record in search_library(backend, [SearchQuery(bpm_min=123)])[0].records] == [123.0, 123.5]
    assert [record.bpm for record in search_library(backend, [SearchQuery(bpm_min=122, bpm_max=122.5)])[0].records] == [
        122.0,
        122.5,
    ]
    assert len(search_library(backend, [SearchQuery(key="8A")])[0].records) == 4
    assert search_library(backend, [SearchQuery(key="9A")])[0].records == ()


def test_a_track_the_plan_excludes_is_never_offered(setup):
    backend, _, _ = setup
    assert backend.plan is not None
    assert backend.review is not None
    excluded = next(
        record
        for record in backend._records(checked=frozenset())
        if record.path not in listed_paths(backend) and record.metadata_status == "complete"
    )
    backend.plan = backend.plan.model_copy(
        update={
            "intent": backend.plan.intent.model_copy(update={"excluded_paths": {excluded.path}}),
        }
    )
    records = search_library(backend, [SearchQuery()])[0].records
    assert excluded.path not in {record.path for record in records}
    assert len(records) == 3


def test_each_search_is_capped_at_twenty_results(wide_setup):
    backend, _ = wide_setup
    records = search_library(backend, [SearchQuery(query="extra")])[0].records
    assert len(records) == MAX_SEARCH_RESULTS == 20


def test_a_public_result_carries_the_reference_and_the_listed_fields_and_no_identity(setup):
    backend, _, root = setup
    record = search_library(backend, [SearchQuery(query="test 5")])[0].records[0]
    result = public_result("L1", record)
    assert set(result) == {"reference", "title", "artist", "genre", "bpm", "key", "energy", "duration"}
    assert result["reference"] == "L1" and result["title"] == "Electron test 5"
    published = json.dumps(result)
    assert str(root) not in published and ".flac" not in published
    for track in backend._records(checked=frozenset()):
        assert public_result("L1", track)["title"] != track.path


def test_two_searches_run_in_order_and_report_how_many_each_found(setup):
    backend, _, _ = setup
    matches = search_library(backend, [SearchQuery(query="test 5"), SearchQuery(genre="Techno", bpm_min=120)])
    assert [len(match.records) for match in matches] == [1, 0]
    assert [match.public() for match in matches] == [
        {"query": "test 5", "resultCount": 1},
        {"query": "", "genre": "Techno", "bpmMin": 120.0, "resultCount": 0},
    ]


def test_a_search_without_a_review_returns_nothing(tmp_path):
    backend = HeadlessBackend(tmp_path / "empty")
    assert search_library(backend, [SearchQuery()])[0].records == ()
    assert (tmp_path / "empty").exists()
