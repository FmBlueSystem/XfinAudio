"""One confirmed export of a split set writes a crate tree, all or nothing (S4, S5, S6).

With a segment size the parent crate holds every track and one child crate per segment
lives under it. The preview lists every crate the confirmation will create or replace,
one confirmation writes them all under the same Serato-running guard, a failure anywhere
puts the folder back exactly as it was, and the receipt names every crate written while
«Mostrar en Finder» keeps revealing the parent.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.test_headless_backend import tagged_flac
from xfinaudio.exporting.serato_crate import (
    SeratoExportPlan,
    build_serato_crate_bytes,
    parse_serato_crate_bytes,
)
from xfinaudio.headless import serato_export as serato_export_module
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_source import ExportSource
from xfinaudio.quality.dj_readiness import DjReadinessCheck

PARENT = "XfinAudio%%Sesión 14-nov"
CHILD_1 = f"{PARENT}%%1 (1-5)"
CHILD_2 = f"{PARENT}%%2 (6-10)"
CHILD_3 = f"{PARENT}%%3 (11-12)"
SEGMENT_ERROR = "segment size must be an integer between 2 and 50 tracks"


def _fixture(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, object], str, Path]:
    """A scanned library of twelve tracks, a twelve-track review and a registered destination."""
    music = tmp_path / "music"
    for index in range(12):
        tagged_flac(music / f"{index}.flac", index)
    serato = tmp_path / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    review = backend.execute("prep.generate", {"targetTrackCount": 12})
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    return backend, {"kind": "review", "reviewId": review["reviewId"]}, destination["destinationId"], subcrates


def _preview(
    backend: HeadlessBackend,
    source: dict[str, object],
    destination_id: str,
    **extra: object,
) -> dict[str, object]:
    return backend.execute("serato.preview", {"source": source, "destinationId": destination_id, **extra})


def _commit(backend: HeadlessBackend, preview: dict[str, object]) -> dict[str, object]:
    return backend.execute("serato.commit", {"previewId": preview["previewId"], "confirmed": True})


def _crates(subcrates: Path) -> list[str]:
    return sorted(path.name for path in subcrates.iterdir() if path.name.endswith(".crate"))


def _paths(subcrates: Path, name: str) -> tuple[str, ...]:
    return parse_serato_crate_bytes((subcrates / f"{name}.crate").read_bytes()).paths


def test_a_split_preview_lists_the_parent_and_every_child_with_its_track_count(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)

    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)

    # The parent comes first and holds the whole set; the children follow in segment order.
    assert preview["crates"] == [
        {"name": f"{PARENT}.crate", "trackCount": 12, "action": "create"},
        {"name": f"{CHILD_1}.crate", "trackCount": 5, "action": "create"},
        {"name": f"{CHILD_2}.crate", "trackCount": 5, "action": "create"},
        {"name": f"{CHILD_3}.crate", "trackCount": 2, "action": "create"},
    ]
    # «Mostrar en Finder» and the confirmation keep naming the parent crate.
    assert preview["filename"] == f"{PARENT}.crate"
    assert preview["trackCount"] == 12
    assert preview["parentsToCreate"] == ["XfinAudio"]
    assert preview["canCommit"] is True
    # The preview only lists: nothing is written before the confirmation.
    assert _crates(subcrates) == []


def test_a_confirmed_split_writes_the_parent_then_each_child_with_exact_bytes(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)

    receipt = _commit(backend, preview)

    segments = [_paths(subcrates, name) for name in (CHILD_1, CHILD_2, CHILD_3)]
    assert [len(segment) for segment in segments] == [5, 5, 2]
    # The parent holds the whole set in the reviewed order; each child its own segment.
    parent = _paths(subcrates, PARENT)
    assert len(parent) == 12
    assert parent == tuple(path for segment in segments for path in segment)
    # Every crate is exactly the artifact the plan promised.
    assert (subcrates / f"{CHILD_1}.crate").read_bytes() == build_serato_crate_bytes(segments[0])
    assert (subcrates / f"{CHILD_3}.crate").read_bytes() == build_serato_crate_bytes(segments[2])
    assert receipt["filename"] == f"{PARENT}.crate"
    assert receipt["validated"] is True
    assert receipt["parentsCreated"] == ["XfinAudio"]
    assert _crates(subcrates) == sorted(
        ["XfinAudio.crate", f"{PARENT}.crate", f"{CHILD_1}.crate", f"{CHILD_2}.crate", f"{CHILD_3}.crate"]
    )


def test_the_receipt_names_every_crate_written_with_its_track_count(tmp_path: Path) -> None:
    backend, source, destination_id, _subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)

    receipt = _commit(backend, preview)

    assert receipt["files"] == [
        {"name": f"{PARENT}.crate", "trackCount": 12},
        {"name": f"{CHILD_1}.crate", "trackCount": 5},
        {"name": f"{CHILD_2}.crate", "trackCount": 5},
        {"name": f"{CHILD_3}.crate", "trackCount": 2},
    ]
    # The receipt still resolves to the parent, the file «Mostrar en Finder» reveals.
    resolved = backend.execute("serato.receipt.resolve", {"receiptId": receipt["receiptId"]})
    assert resolved["path"] == str(_subcrates / f"{PARENT}.crate")


def test_a_child_that_changed_after_the_preview_keeps_the_stale_preview_refusal(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)
    (subcrates / f"{CHILD_2}.crate").write_bytes(b"created by someone else meanwhile")

    with pytest.raises(BackendError) as failure:
        _commit(backend, preview)

    assert failure.value.code == "stale_destination"
    assert _crates(subcrates) == [f"{CHILD_2}.crate"]


def test_a_commit_while_serato_runs_writes_no_crate_of_the_tree(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)
    backend.serato.serato_running = lambda: True

    with pytest.raises(BackendError) as failure:
        _commit(backend, preview)

    assert failure.value.code == "serato_running"
    assert _crates(subcrates) == []


def test_a_failure_on_the_third_child_rolls_the_whole_tree_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    replaced = subcrates / f"{CHILD_3}.crate"
    earlier = b"an earlier child crate"
    replaced.write_bytes(earlier)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)
    monkeypatch.setattr(
        serato_export_module,
        "validate_serato_round_trip",
        lambda plan, *, volume_root=None: DjReadinessCheck(
            label="Verificación Serato",
            status="blocked" if plan.target_path.name == f"{CHILD_3}.crate" else "ready",
            detail="forced post-write validation failure",
        ),
    )

    with pytest.raises(BackendError) as failure:
        _commit(backend, preview)

    assert failure.value.code == "export_failed"
    assert str(failure.value) == "The crate could not be exported safely; inspect local diagnostics before retrying"
    # Every crate this export created is gone, the replaced one is back byte for byte,
    # and the ancestor crate it created for the tree is gone too.
    assert _crates(subcrates) == [f"{CHILD_3}.crate"]
    assert replaced.read_bytes() == earlier
    assert not (subcrates / f"{PARENT}.crate").exists()
    assert not (subcrates / "XfinAudio.crate").exists()


def test_replaying_a_confirmed_tree_returns_the_same_receipt_without_writing_again(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)
    receipt = _commit(backend, preview)
    written = {path.name: path.read_bytes() for path in subcrates.iterdir()}

    replayed = _commit(backend, preview)

    assert replayed == receipt
    assert {path.name: path.read_bytes() for path in subcrates.iterdir()} == written


def test_a_segment_size_at_least_the_track_count_previews_the_parent_only(tmp_path: Path) -> None:
    backend, source, destination_id, _subcrates = _fixture(tmp_path)

    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=50)

    assert preview["crates"] == [{"name": f"{PARENT}.crate", "trackCount": 12, "action": "create"}]


@pytest.mark.parametrize("segment_size", [1, 51, 0, -5, "5", 5.0, True])
def test_an_invalid_segment_size_is_refused_at_the_protocol_boundary(tmp_path: Path, segment_size: object) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)

    with pytest.raises(BackendError) as failure:
        _preview(backend, source, destination_id, name=PARENT, segmentSize=segment_size)

    assert failure.value.code == "invalid_params"
    assert str(failure.value) == SEGMENT_ERROR
    assert _crates(subcrates) == []


def test_a_split_is_refused_for_a_metadata_worklist(tmp_path: Path) -> None:
    music = tmp_path / "music"
    for index in range(3):
        tagged_flac(music / f"{index}.flac", index)
    serato = tmp_path / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    rows = backend.execute("library.scan", {"root": str(music)})["tracks"]
    source: dict[str, object] = {
        "kind": "metadata",
        "status": "complete",
        "missingField": None,
        "trackIds": [row["id"] for row in rows],
    }
    destination_id = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})["destinationId"]

    with pytest.raises(BackendError) as failure:
        _preview(backend, source, destination_id, segmentSize=5)

    assert failure.value.code == "invalid_params"
    assert _crates(subcrates) == []


def test_a_null_segment_size_keeps_todays_single_crate(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)

    # A shell that serializes "no choice" as null gets today's preview, not a refusal.
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=None)

    assert "crates" not in preview
    assert preview["filename"] == f"{PARENT}.crate"
    assert _crates(subcrates) == []


def test_an_export_without_a_segment_size_keeps_todays_preview_commit_and_receipt(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT)

    # No split means no tree fields at all, and the same summary as before the option existed.
    assert "crates" not in preview
    assert preview["filename"] == f"{PARENT}.crate"
    assert preview["trackCount"] == 12
    assert preview["parentsToCreate"] == ["XfinAudio"]
    assert preview["backup"] == {"required": False}

    receipt = _commit(backend, preview)

    assert "files" not in receipt
    assert receipt["filename"] == f"{PARENT}.crate"
    assert receipt["trackCount"] == 12
    assert _crates(subcrates) == sorted(["XfinAudio.crate", f"{PARENT}.crate"])


def _tree_of_five(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, object], str, Path]:
    """A twenty-track review split in four: the five-crate tree measured on the external drive."""
    music = tmp_path / "music"
    for index in range(20):
        tagged_flac(music / f"{index}.flac", index)
    serato = tmp_path / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    review = backend.execute("prep.generate", {"targetTrackCount": 20})
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    return backend, {"kind": "review", "reviewId": review["reviewId"]}, destination["destinationId"], subcrates


def _count_source_reloads(monkeypatch: pytest.MonkeyPatch) -> Callable[[], int]:
    """Count the full source reloads a later call makes; the source itself loads as always."""
    reloads: list[object] = []
    original = serato_export_module.load_source

    def counting(backend: HeadlessBackend, value: Any, **options: Any) -> ExportSource:
        reloads.append(value)
        return original(backend, value, **options)

    monkeypatch.setattr(serato_export_module, "load_source", counting)
    return lambda: len(reloads)


def test_one_confirmed_tree_reads_the_source_once_for_the_whole_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, source, destination_id, subcrates = _tree_of_five(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)
    planned = preview["crates"]
    assert isinstance(planned, list)
    assert len(planned) == 5
    reloads = _count_source_reloads(monkeypatch)

    receipt = _commit(backend, preview)

    # Five crates plus the ancestor crate they need, verified as one source.
    files = receipt["files"]
    assert isinstance(files, list)
    assert len(files) == 5
    assert len(_crates(subcrates)) == 6
    assert reloads() == 1


def test_one_confirmed_single_crate_reads_the_source_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT)
    reloads = _count_source_reloads(monkeypatch)

    receipt = _commit(backend, preview)

    assert receipt["filename"] == f"{PARENT}.crate"
    assert _crates(subcrates) == sorted(["XfinAudio.crate", f"{PARENT}.crate"])
    assert reloads() == 1


def test_a_source_track_that_changes_mid_tree_still_rolls_the_whole_tree_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, source, destination_id, subcrates = _fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name=PARENT, segmentSize=5)
    track = tmp_path / "music" / "0.flac"
    validated = serato_export_module.validate_serato_round_trip

    def validate_then_change_one_track(plan: SeratoExportPlan, *, volume_root: Path | None = None) -> DjReadinessCheck:
        check = validated(plan, volume_root=volume_root)
        # One crate has landed and is validated; the scanned file changes before the next write.
        stamp = track.stat()
        os.utime(track, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000))
        return check

    monkeypatch.setattr(serato_export_module, "validate_serato_round_trip", validate_then_change_one_track)

    with pytest.raises(BackendError) as failure:
        _commit(backend, preview)

    assert failure.value.code == "stale_source"
    assert str(failure.value) == "The crate could not be exported safely; inspect local diagnostics before retrying"
    # Nothing of the tree survives a source that moved under the commit.
    assert _crates(subcrates) == []
