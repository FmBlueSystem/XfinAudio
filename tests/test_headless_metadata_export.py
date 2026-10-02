"""Metadata-only repair worklists use the existing confirmed safe crate path."""

from __future__ import annotations

import hashlib

import pytest
from mutagen.flac import FLAC

from tests.test_headless_backend import tagged_flac
from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError


@pytest.fixture
def worklist(tmp_path):
    music = tmp_path / "music"
    for i in range(3):
        tagged_flac(music / f"{i}.flac", i)
    for i in (0, 1):
        tags = FLAC(music / f"{i}.flac")
        del tags["bpm"]
        tags.save()
    serato = tmp_path / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)
    (serato / "database V2").write_bytes(b"untouched database sentinel")
    backend = HeadlessBackend(tmp_path / "data")
    rows = backend.execute("library.scan", {"root": str(music)})["tracks"]
    ids = {t["title"]: t["id"] for t in rows}
    source = {
        "kind": "metadata",
        "status": "incomplete",
        "missingField": "bpm",
        "trackIds": [ids["Track 0"], ids["Track 1"]],
    }
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*music.iterdir(), serato / "database V2"]}
    return backend, source, destination, serato, before, ids


def preview(fixture, source=None):
    backend, chosen, destination, *_ = fixture
    return backend.execute(
        "serato.preview",
        {"source": source or chosen, "destinationId": destination["destinationId"], "name": "Repair fixture"},
    )


def test_metadata_preview_is_readonly_and_honest(worklist):
    item = preview(worklist)
    assert item["canCommit"] and item["readiness"] == "needs_review"
    assert item["trackCount"] == 2 and item["blockers"] == []
    assert any("metadatos" in s.lower() for s in item["warnings"])
    assert all(str(p) not in str(item) for p in worklist[4])
    assert list((worklist[3] / "Subcrates").iterdir()) == []
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in worklist[4].items())


def test_metadata_commit_requires_confirmation_and_retains_backup(worklist):
    backend = worklist[0]
    item = preview(worklist)
    with pytest.raises(BackendError, match="Confirm"):
        backend.execute("serato.commit", {"previewId": item["previewId"], "confirmed": False})
    first = backend.execute("serato.commit", {"previewId": item["previewId"], "confirmed": True})
    crate = worklist[3] / "Subcrates" / first["filename"]
    original = crate.read_bytes()
    parsed = parse_serato_crate_bytes(original)
    assert len(parsed.paths) == 2
    assert all(any(p.endswith(f"music/{i}.flac") for p in parsed.paths) for i in (0, 1))
    item = preview(worklist)
    second = backend.execute("serato.commit", {"previewId": item["previewId"], "confirmed": True})
    assert second["backupCreated"] and original in [p.read_bytes() for p in crate.parent.iterdir() if p != crate]
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in worklist[4].items())


@pytest.mark.parametrize(
    "change",
    [
        {"trackIds": []},
        {"trackIds": ["0" * 64]},
        {"missingField": "artist"},
        {"status": "all"},
        {"extra": "forbidden"},
        {"confirmed": True},
    ],
)
def test_metadata_selector_rejects_untrusted_scope(worklist, change):
    with pytest.raises(BackendError):
        preview(worklist, {**worklist[1], **change})


def test_metadata_selector_rejects_duplicates_and_complete_mismatch(worklist):
    for ids in [[worklist[1]["trackIds"][0]] * 2, [worklist[5]["Track 2"]]]:
        with pytest.raises(BackendError):
            preview(worklist, {**worklist[1], "trackIds": ids})


def test_complete_metadata_worklist_is_also_not_a_dj_readiness_claim(worklist):
    item = preview(
        worklist, {"kind": "metadata", "status": "complete", "missingField": None, "trackIds": [worklist[5]["Track 2"]]}
    )
    assert item["canCommit"] and item["readiness"] == "needs_review" and item["trackCount"] == 1


def test_metadata_source_change_invalidates_confirmed_preview(worklist):
    item = preview(worklist)
    path = next(p for p in worklist[4] if p.name == "0.flac")
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(BackendError):
        worklist[0].execute("serato.commit", {"previewId": item["previewId"], "confirmed": True})
    assert list((worklist[3] / "Subcrates").iterdir()) == []


@pytest.mark.parametrize(
    "change",
    [
        {"trackIds": "not-an-array"},
        {"trackIds": [None]},
        {"trackIds": [["unhashable"]]},
        {"trackIds": ["0" * 64] * 501},
        {"missingField": []},
        {"status": []},
        {"status": "complete", "missingField": "bpm"},
    ],
)
def test_metadata_selector_rejects_malformed_values_without_unhandled_errors(worklist, change):
    with pytest.raises(BackendError):
        preview(worklist, {**worklist[1], **change})


def test_metadata_selection_exact_subset_does_not_expand_on_export(worklist):
    selected = {**worklist[1], "trackIds": [worklist[1]["trackIds"][1]]}
    item = preview(worklist, selected)
    assert item["trackCount"] == 1
    receipt = worklist[0].execute("serato.commit", {"previewId": item["previewId"], "confirmed": True})
    crate = worklist[3] / "Subcrates" / receipt["filename"]
    assert parse_serato_crate_bytes(crate.read_bytes()).paths[0].endswith("music/1.flac")
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in worklist[4].items())
