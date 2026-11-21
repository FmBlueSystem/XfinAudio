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
from tests.test_headless_list_chat import ChatTransport, call, turn
from xfinaudio.ai import nan_client
from xfinaudio.ai.list_chat import SearchQuery
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.library_search import MAX_SEARCH_RESULTS, public_result, search_library
from xfinaudio.headless.optional_ai import OptionalAI


def forbidden(*args, **kwargs):
    raise AssertionError("Real provider requests are forbidden")


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
    assert set(result) == {"reference", "title", "artist", "genre", "bpm", "key", "energy", "duration", "year"}
    assert result["reference"] == "L1" and result["title"] == "Electron test 5"
    assert result["year"] is None
    assert public_result("L1", record.model_copy(update={"release_year": 1985}))["year"] == 1985
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


#: The two searches the real provider wrote: every field, most of them unused.
REAL_SEARCHES = (
    ({"query": "Madonna", "genre": "", "bpmMin": 127, "bpmMax": 133, "key": ""}, "Holiday", "Madonna"),
    (
        {"query": "Whitney Houston", "genre": "", "bpmMin": 0, "bpmMax": 0, "key": ""},
        "I Wanna Dance with Somebody",
        "Whitney Houston",
    ),
)


@pytest.fixture
def real_search_chat(tmp_path, monkeypatch):
    """A chat facade over a library that holds the two tracks those searches look for."""
    root = tmp_path / "music"
    shutil.copytree(FIXTURES, root)
    for name, title, artist, bpm, key in (
        ("madonna.flac", "Holiday", "Madonna", "128", "9A"),
        ("whitney.flac", "I Wanna Dance with Somebody", "Whitney Houston", "122", "4B"),
    ):
        copy = root / name
        shutil.copyfile(root / "track-5.flac", copy)
        tags = FLAC(copy)
        tags["title"], tags["artist"], tags["genre"] = title, artist, "Pop"
        tags["bpm"], tags["initialkey"] = bpm, key
        tags.save()
    monkeypatch.setattr(nan_client, "_urlopen", forbidden)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    review = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Real searches"})
    transport = ChatTransport()
    facade = OptionalAI(backend, transport=transport)
    credential = tmp_path / "dummy-selected.env"
    credential.write_bytes(b"NAN_API_KEY=synthetic-test-only\n")
    credential.chmod(0o600)
    status = call(facade, "ai.status")
    selected = call(facade, "ai.credential.set", {"revision": status["revision"], "path": str(credential)})
    call(facade, "ai.settings.update", {"revision": selected["revision"], "enabled": True})
    return facade, transport, backend, review["reviewId"]


@pytest.mark.parametrize(("search", "title", "artist"), REAL_SEARCHES, ids=["madonna", "whitney"])
def test_a_real_search_object_runs_and_its_results_reach_the_second_request(real_search_chat, search, title, artist):
    facade, transport, backend, review_id = real_search_chat
    transport.replies = [
        json.dumps({"reply": "Busco en la biblioteca.", "actions": [], "searches": [search]}),
        json.dumps({"reply": "Encontré esa pista.", "actions": []}),
    ]
    result = turn(facade, review_id)["result"]
    # The search ran: the provider is asked once more, with the results attached.
    assert len(transport.bodies) == 2
    second = transport.bodies[1]["messages"]
    assert [message["role"] for message in second] == ["system", "user", "user"]
    results = json.loads(second[-1]["content"].split("\n", 1)[1])
    assert [item["title"] for item in results] == [title]
    assert results[0]["artist"] == artist
    assert set(results[0]) == {"reference", "title", "artist", "genre", "bpm", "key", "energy", "duration", "year"}
    assert result["text"] == "Encontré esa pista."


@pytest.fixture
def year_setup(tmp_path):
    """A library where two eligible tracks carry a release year and the rest do not."""
    root = tmp_path / "music"
    shutil.copytree(FIXTURES, root)
    for index, year in ((1, 1985), (2, 1994)):
        copy = root / f"year-{index}.flac"
        shutil.copyfile(root / "track-5.flac", copy)
        tags = FLAC(copy)
        tags["title"] = f"Year test {index}"
        tags["date"] = str(year)
        tags.save()
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Years"})
    return backend


def test_a_search_carries_the_release_year_of_each_result_and_nothing_when_it_is_unknown(year_setup):
    records = search_library(year_setup, [SearchQuery(query="year test")])[0].records
    assert [(record.title, record.release_year) for record in records] == [("Year test 1", 1985), ("Year test 2", 1994)]
    results = [public_result(f"L{index}", record) for index, record in enumerate(records, start=1)]
    assert [result["year"] for result in results] == [1985, 1994]
    unknown = search_library(year_setup, [SearchQuery(query="test 5")])[0].records[0]
    assert public_result("L9", unknown)["year"] is None


def test_a_year_range_returns_only_tracks_with_a_year_inside_it(year_setup):
    within = search_library(year_setup, [SearchQuery(year_min=1980, year_max=1990)])[0].records
    titles = [record.title for record in within]
    assert titles == ["Year test 1"]
    assert [record.title for record in search_library(year_setup, [SearchQuery(year_min=1990)])[0].records] == [
        "Year test 2"
    ]
    assert [record.title for record in search_library(year_setup, [SearchQuery(year_max=1900)])[0].records] == []
    # Without a year limit the tracks without a year are still offered.
    without = search_library(year_setup, [SearchQuery(query="test 5")])[0].records
    assert [record.title for record in without] == ["Electron test 5"]
