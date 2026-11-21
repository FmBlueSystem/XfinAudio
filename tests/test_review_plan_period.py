"""S17: a list generated with a release period keeps its engine picks inside it."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity
from xfinaudio.ai import nan_client
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken

# The period the DJ typed into the Prep form, and the library tracks on both sides of it.
PERIOD = {"yearMin": 1980, "yearMax": 1989}
IN_PERIOD = (1984, 1985, 1986, 1987, 1988, 1989, 1983, 1982, 1981, 1980)
OUTSIDE = (1970, 1975, 1995, 2000, 2005, 2010)
QUESTION = "Busca otra pista que encaje."


def seeded(tmp_path: Path) -> tuple[HeadlessBackend, list[TrackRecord], dict[str, int]]:
    """A library with tracks inside and outside 1980-1989, all fully described."""
    root = tmp_path / "music"
    root.mkdir()
    records = [
        TrackRecord(
            path=str(root / f"{index:03}.flac"),
            title=f"Track {year} {index}",
            artist=f"Artist {year}",
            bpm=120 + index,
            camelot_key="8A" if index % 2 == 0 else "8B",
            energy_level=5,
            duration=240,
            genre="House",
            metadata_status="complete",
            release_year=year,
        )
        for index, year in enumerate((*IN_PERIOD, *OUTSIDE))
    ]
    for record in records:
        Path(record.path).touch()
    backend = HeadlessBackend(tmp_path / "data")
    backend.roots = [root]
    backend.repository.save_scan_results(records)
    year_of = {identity(record): record.release_year for record in records if record.release_year is not None}
    return backend, records, year_of


def generated(backend: HeadlessBackend, target: int = 3, **period: int) -> dict:
    return backend.execute("prep.generate", {"targetTrackCount": target, "name": "Época", **period})


def years_of(result: dict, year_of: dict[str, int]) -> set[int | None]:
    return {year_of.get(track["id"]) for track in result["tracks"]}


def test_extend_picks_only_tracks_inside_the_plan_period(tmp_path: Path) -> None:
    backend, _, year_of = seeded(tmp_path)
    result = generated(backend, **PERIOD)
    # Ten library tracks are inside 1980-1989, three of them already listed: the growth
    # stops when they run out instead of reaching the requested 13 with outside tracks.
    grew = backend.execute("review.extend", {"reviewId": result["reviewId"], "targetTrackCount": 13})
    assert grew["extended"] == {"requested": 10, "added": len(IN_PERIOD) - len(result["tracks"]), "outsideGenre": 0}
    assert len(grew["tracks"]) == len(IN_PERIOD)
    assert years_of(grew, year_of) <= set(IN_PERIOD)


def test_compare_and_replace_offer_only_a_track_inside_the_plan_period(tmp_path: Path) -> None:
    backend, _, year_of = seeded(tmp_path)
    result = generated(backend, **PERIOD)
    target = result["tracks"][1]["id"]
    comparison = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": target})
    assert comparison["available"] is True
    offered = comparison["replacement"]
    assert year_of[offered["id"]] in IN_PERIOD
    applied = backend.execute(
        "review.replace",
        {"reviewId": comparison["reviewId"], "trackId": target, "replacementId": offered["id"]},
    )
    assert applied["tracks"][1]["id"] == offered["id"]
    assert years_of(applied, year_of) <= set(IN_PERIOD)


def test_remove_replaces_with_a_track_inside_the_plan_period(tmp_path: Path) -> None:
    backend, _, year_of = seeded(tmp_path)
    result = generated(backend, **PERIOD)
    updated = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": result["tracks"][1]["id"]})
    assert len(updated["tracks"]) == len(result["tracks"])
    assert updated["tracks"][1]["id"] != result["tracks"][1]["id"]
    assert years_of(updated, year_of) <= set(IN_PERIOD)


def test_insert_of_a_track_outside_the_plan_period_is_still_allowed(tmp_path: Path) -> None:
    backend, records, _ = seeded(tmp_path)
    result = generated(backend, **PERIOD)
    chosen = identity(records[len(IN_PERIOD) + 1])
    updated = backend.execute("review.insert", {"reviewId": result["reviewId"], "trackId": chosen, "position": 2})
    assert [track["id"] for track in updated["tracks"]][1] == chosen
    assert len(updated["tracks"]) == len(result["tracks"]) + 1


def test_swap_to_a_track_outside_the_plan_period_is_still_allowed(tmp_path: Path) -> None:
    backend, records, _ = seeded(tmp_path)
    result = generated(backend, **PERIOD)
    chosen = identity(records[len(IN_PERIOD) + 3])
    updated = backend.execute(
        "review.swap",
        {"reviewId": result["reviewId"], "trackId": result["tracks"][1]["id"], "replacementTrackId": chosen},
    )
    assert updated["tracks"][1]["id"] == chosen


def test_a_list_generated_without_a_period_still_lets_the_engine_pick_outside_tracks(
    tmp_path: Path,
) -> None:
    backend, _, year_of = seeded(tmp_path)
    result = generated(backend, target=10)
    grew = backend.execute("review.extend", {"reviewId": result["reviewId"], "targetTrackCount": 13})
    assert len(grew["tracks"]) == 13
    assert years_of(grew, year_of) & set(OUTSIDE)
    # No period is stored, so a restart recomputes and keeps the same plan.
    assert backend.plan.intent.year_min is None and backend.plan.intent.year_max is None


class ChatTransport:
    """Fake provider that records every request and answers with the queued replies."""

    def __init__(self) -> None:
        self.replies: list[str] = []
        self.bodies: list[dict] = []

    def __call__(self, request, *, timeout):
        self.bodies.append(json.loads(request.data.decode("utf-8")))
        content = self.replies.pop(0)
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": content}}]}).encode())


def forbidden(*args, **kwargs):
    raise AssertionError("Real provider requests are forbidden")


@pytest.fixture
def chat_setup(tmp_path: Path, monkeypatch) -> tuple[HeadlessBackend, object, ChatTransport, list[TrackRecord]]:
    from xfinaudio.headless.optional_ai import OptionalAI

    monkeypatch.setattr(nan_client, "_urlopen", forbidden)
    backend, records, _ = seeded(tmp_path)
    transport = ChatTransport()
    facade = OptionalAI(backend, transport=transport)
    credential_path = tmp_path / "dummy-selected.env"
    credential_path.write_bytes(b"NAN_API_KEY=synthetic-test-only\n")
    credential_path.chmod(0o600)
    status = call(facade, "ai.status")
    selected = call(facade, "ai.credential.set", {"revision": status["revision"], "path": str(credential_path)})
    call(facade, "ai.settings.update", {"revision": selected["revision"], "enabled": True})
    generated(backend, **PERIOD)
    return backend, facade, transport, records


def call(facade, method: str, params: dict | None = None) -> dict:
    return facade.execute(method, params or {}, ScanCancellationToken(), lambda _: None)


def test_the_assistant_search_only_finds_tracks_inside_the_plan_period(chat_setup) -> None:
    backend, facade, transport, records = chat_setup
    transport.replies = [
        json.dumps({"reply": "Busco en la biblioteca.", "actions": [], "searches": [{"query": "Track"}]}),
        json.dumps({"reply": "Estas son las pistas.", "actions": []}),
    ]
    prepared = call(
        facade, "ai.prepare", {"surface": "chat", "request": QUESTION, "context": {"reviewId": backend.review_id}}
    )
    call(facade, "ai.run", {"previewId": prepared["previewId"], "confirmed": True})
    # The search ran: two requests, the second carrying the local results.
    assert len(transport.bodies) == 2
    results = json.loads(transport.bodies[1]["messages"][-1]["content"].split("\n", 1)[1])
    assert results
    assert {item["year"] for item in results} <= set(IN_PERIOD)
    listed = {track.title for track in backend.review.recommendation.ordered_tracks}
    outside_titles = {record.title for record in records if record.release_year in OUTSIDE}
    assert {item["title"] for item in results}.isdisjoint(outside_titles)
    assert {item["title"] for item in results}.isdisjoint(listed)


def test_an_open_period_generated_with_one_bound_keeps_its_own_range(tmp_path: Path) -> None:
    backend, _, year_of = seeded(tmp_path)
    result = generated(backend, target=2, yearMin=1990)
    above_1990 = {year for year in OUTSIDE if year >= 1990}
    grew = backend.execute("review.extend", {"reviewId": result["reviewId"], "targetTrackCount": 8})
    assert len(grew["tracks"]) == len(above_1990)
    assert years_of(grew, year_of) <= above_1990
