"""Persist original build context without sharing paths or dropping unavailable locks."""

import json
from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError


def save(backend, current_revision, **patch):
    return backend.execute(
        "prep.settings.update",
        {
            "revision": current_revision,
            "requiredTrackIds": [],
            "excludedTrackIds": [],
            "genreFocus": "",
            "clearUnavailable": False,
            **patch,
        },
    )


def test_prep_controls_roundtrip_restart_with_no_credentials_or_source_writes(tmp_path):
    backend, records = seeded(tmp_path)
    original = [Path(r.path).read_bytes() for r in records]
    snapshot = backend.execute("prep.settings.get", {})
    updated = save(
        backend,
        snapshot["revision"],
        requiredTrackIds=[identity(records[0])],
        excludedTrackIds=[identity(records[1])],
        genreFocus="House",
    )
    assert updated["requiredTrackIds"] == [identity(records[0])]
    assert updated["excludedTrackIds"] == [identity(records[1])]
    restarted = HeadlessBackend(backend.data_dir)
    restarted.roots = backend.roots
    assert restarted.execute("prep.settings.get", {}) == updated
    assert str(tmp_path) not in json.dumps(updated)
    assert original == [Path(r.path).read_bytes() for r in records]
    assert backend.preferences.settings.build.locked_paths == frozenset({records[0].path})


def test_unavailable_controls_are_counted_preserved_and_only_explicitly_cleared(tmp_path):
    backend, records = seeded(tmp_path)
    snapshot = backend.execute("prep.settings.get", {})
    save(backend, snapshot["revision"], requiredTrackIds=[identity(records[0])])
    Path(records[0].path).unlink()
    snapshot = backend.execute("prep.settings.get", {})
    assert snapshot["requiredTrackIds"] == []
    assert snapshot["unavailableRequiredCount"] == 1
    updated = save(backend, snapshot["revision"], genreFocus="Techno")
    assert updated["unavailableRequiredCount"] == 1
    updated = save(backend, updated["revision"], clearUnavailable=True)
    assert updated["unavailableRequiredCount"] == 0


def test_stale_unknown_and_conflicting_prep_updates_fail_without_mutation(tmp_path):
    backend, records = seeded(tmp_path)
    snapshot = backend.execute("prep.settings.get", {})
    saved = save(backend, snapshot["revision"], genreFocus="House")
    for patch in [
        {"revision": snapshot["revision"]},
        {"requiredTrackIds": ["0" * 64]},
        {"requiredTrackIds": [identity(records[0])], "excludedTrackIds": [identity(records[0])]},
        {"clearUnavailable": "yes"},
    ]:
        with pytest.raises(BackendError):
            save(backend, saved["revision"], **patch)
    assert backend.execute("prep.settings.get", {}) == saved


def test_reauthorization_restores_missing_controls_without_new_save(tmp_path):
    backend, records = seeded(tmp_path)
    initial = backend.execute("prep.settings.get", {})
    updated = save(backend, initial["revision"], requiredTrackIds=[identity(records[0])])
    roots = backend.roots
    backend.roots = []
    unavailable = backend.execute("prep.settings.get", {})
    assert unavailable["requiredTrackIds"] == []
    assert unavailable["unavailableRequiredCount"] == 1
    assert unavailable["revision"] == updated["revision"]
    backend.roots = roots
    assert backend.execute("prep.settings.get", {}) == updated
