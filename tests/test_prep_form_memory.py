"""The last successful Prep form is remembered and offered again on the next start."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError

FORM_FIELDS = {
    "targetTrackCount",
    "targetMinutes",
    "strategy",
    "slotRole",
    "name",
    "startTrackId",
    "endTrackId",
}


def generate(backend: HeadlessBackend, **patch):
    return backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Club", **patch})


def snapshot(backend: HeadlessBackend) -> dict:
    return backend.execute("prep.settings.get", {})


def last_form(backend: HeadlessBackend) -> dict:
    current = snapshot(backend)
    assert "lastForm" in current
    return current["lastForm"]


def test_a_successful_generation_remembers_the_form_for_the_next_start(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path)
    generate(
        backend,
        targetMinutes=90,
        strategy="warmup",
        slotRole="warmup",
        startTrackId=identity(records[0]),
        endTrackId=identity(records[1]),
    )
    expected = {
        "targetTrackCount": 4,
        "targetMinutes": 90,
        "strategy": "warmup",
        "slotRole": "warmup",
        "name": "Club",
        "startTrackId": identity(records[0]),
        "endTrackId": identity(records[1]),
    }
    current = snapshot(backend)
    assert current.get("lastForm") == expected
    assert str(tmp_path) not in json.dumps(current)
    restarted = HeadlessBackend(backend.data_dir)
    restarted.roots = backend.roots
    assert last_form(restarted) == expected


def test_an_untouched_form_is_reported_with_every_field_empty(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    form = last_form(backend)
    assert set(form) == FORM_FIELDS
    assert all(value is None for value in form.values())


def test_a_refused_generation_remembers_nothing_and_keeps_the_previous_form(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    generate(backend, name="Primera")
    before = snapshot(backend)
    for refused in (
        {"targetTrackCount": 1},
        {"name": "Segunda", "startTrackId": "0" * 64},
        {"name": "Segunda", "targetMinutes": 0},
    ):
        with pytest.raises(BackendError):
            backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Club", **refused})
    after = snapshot(backend)
    assert after == before
    assert (after.get("lastForm") or {}).get("name") == "Primera"
    assert (after.get("lastForm") or {}).get("startTrackId") is None


def test_saving_the_explicit_controls_and_the_remembered_form_stay_independent(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path)
    generate(backend, name="Primera")
    remembered = last_form(backend)
    current = snapshot(backend)
    updated = backend.execute(
        "prep.settings.update",
        {
            "revision": current["revision"],
            "requiredTrackIds": [identity(records[2])],
            "excludedTrackIds": [],
            "genreFocus": "House",
            "clearUnavailable": False,
        },
    )
    assert updated.get("lastForm") == remembered
    generate(backend, name="Segunda")
    after = snapshot(backend)
    assert after["requiredTrackIds"] == [identity(records[2])]
    assert after["genreFocus"] == "House"
    assert (after.get("lastForm") or {}).get("name") == "Segunda"


def test_a_remembered_track_that_left_the_library_keeps_its_opaque_identity(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path)
    generate(backend, startTrackId=identity(records[0]), endTrackId=identity(records[1]))
    Path(records[0].path).unlink()
    form = last_form(backend)
    assert form["startTrackId"] == identity(records[0])
    assert form["endTrackId"] == identity(records[1])
    assert str(tmp_path) not in json.dumps(form)


def test_the_existing_saved_controls_response_keeps_its_shape(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path)
    current = snapshot(backend)
    assert set(current) == {
        "revision",
        "requiredTrackIds",
        "excludedTrackIds",
        "genreFocus",
        "unavailableRequiredCount",
        "unavailableExcludedCount",
        "lastForm",
    }
    assert current["requiredTrackIds"] == []
    assert current["excludedTrackIds"] == []
    assert current["genreFocus"] == ""
    updated = backend.execute(
        "prep.settings.update",
        {
            "revision": current["revision"],
            "requiredTrackIds": [identity(records[0])],
            "excludedTrackIds": [identity(records[1])],
            "genreFocus": "Techno",
            "clearUnavailable": False,
        },
    )
    assert updated["requiredTrackIds"] == [identity(records[0])]
    assert updated["excludedTrackIds"] == [identity(records[1])]
    assert updated["genreFocus"] == "Techno"
