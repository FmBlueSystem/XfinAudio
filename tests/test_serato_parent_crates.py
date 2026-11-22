"""Nested crate names need their ancestor crates, and the export creates only the missing ones (S11).

A child crate called `XfinAudio%%Harmonic Journey 14-nov` appears in Serato under the
parent crate `XfinAudio`, so a confirmed export creates the parents that are missing,
outermost first, inside the same commit as the child and with the same containment,
symlink and validation rules. An ancestor that already exists is never rewritten,
replaced or backed up.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mutagen.flac import FLAC

from tests.test_headless_backend import tagged_flac
from xfinaudio.exporting.serato_crate import (
    SERATO_CRATE_VERSION,
    build_serato_crate_bytes,
    parse_serato_crate_bytes,
)
from xfinaudio.headless import serato_export as serato_export_module
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.quality.dj_readiness import DjReadinessCheck


def _generated_fixture(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, object], str, Path]:
    """A scanned library, one generated review and a registered destination on the same volume."""
    music = tmp_path / "music"
    for index in range(3):
        tagged_flac(music / f"{index}.flac", index)
    serato = tmp_path / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    review = backend.execute("prep.generate", {"targetTrackCount": 2})
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    return backend, review, destination["destinationId"], subcrates


def _metadata_fixture(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, object], str, Path]:
    """A scanned library whose first two tracks have no BPM, plus a registered destination."""
    music = tmp_path / "music"
    for index in range(3):
        tagged_flac(music / f"{index}.flac", index)
    for index in (0, 1):
        tags = FLAC(music / f"{index}.flac")
        del tags["bpm"]
        tags.save()
    serato = tmp_path / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    rows = backend.execute("library.scan", {"root": str(music)})["tracks"]
    ids = {row["title"]: row["id"] for row in rows}
    source: dict[str, object] = {
        "kind": "metadata",
        "status": "incomplete",
        "missingField": "bpm",
        "trackIds": [ids["Track 0"], ids["Track 1"]],
    }
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    return backend, source, destination["destinationId"], subcrates


def _preview(
    backend: HeadlessBackend,
    source: dict[str, object],
    destination_id: str,
    *,
    name: str | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {"source": source, "destinationId": destination_id}
    if name is not None:
        params["name"] = name
    return backend.execute("serato.preview", params)


def _commit(backend: HeadlessBackend, preview: dict[str, object]) -> dict[str, object]:
    return backend.execute("serato.commit", {"previewId": preview["previewId"], "confirmed": True})


def _crate_names(subcrates: Path) -> list[str]:
    return sorted(path.name for path in subcrates.iterdir())


def test_a_generated_set_preview_lists_the_missing_root_crate(tmp_path: Path) -> None:
    backend, review, destination_id, subcrates = _generated_fixture(tmp_path)

    preview = _preview(backend, {"kind": "review", "reviewId": review["reviewId"]}, destination_id)

    assert preview["filename"].startswith("XfinAudio%%")
    assert preview["parentsToCreate"] == ["XfinAudio"]
    assert preview["canCommit"] is True
    # The preview only plans: nothing is created before the user confirms.
    assert _crate_names(subcrates) == []


def test_a_metadata_worklist_preview_lists_every_missing_ancestor_outermost_first(tmp_path: Path) -> None:
    backend, source, destination_id, _subcrates = _metadata_fixture(tmp_path)

    preview = _preview(backend, source, destination_id, name="XfinAudio%%Metadata%%Pendientes")

    assert preview["filename"] == "XfinAudio%%Metadata%%Pendientes.crate"
    assert preview["parentsToCreate"] == ["XfinAudio", "XfinAudio%%Metadata"]


def test_a_preview_lists_only_the_ancestors_that_are_missing(tmp_path: Path) -> None:
    backend, review, destination_id, subcrates = _generated_fixture(tmp_path)
    (subcrates / "XfinAudio.crate").write_bytes(build_serato_crate_bytes(()))

    generated = _preview(backend, {"kind": "review", "reviewId": review["reviewId"]}, destination_id)

    assert generated["parentsToCreate"] == []

    backend, source, other_destination_id, other_subcrates = _metadata_fixture(tmp_path / "worklist")
    (other_subcrates / "XfinAudio.crate").write_bytes(build_serato_crate_bytes(()))

    worklist = _preview(backend, source, other_destination_id, name="XfinAudio%%Metadata%%Pendientes")

    # The root crate already exists, so only the deeper ancestor is still missing.
    assert worklist["parentsToCreate"] == ["XfinAudio%%Metadata"]


def test_a_confirmed_commit_creates_the_parent_as_a_valid_empty_crate_then_the_child(tmp_path: Path) -> None:
    backend, review, destination_id, subcrates = _generated_fixture(tmp_path)
    preview = _preview(backend, {"kind": "review", "reviewId": review["reviewId"]}, destination_id)

    receipt = _commit(backend, preview)

    parent = parse_serato_crate_bytes((subcrates / "XfinAudio.crate").read_bytes())
    assert parent.version == SERATO_CRATE_VERSION
    assert parent.paths == ()
    child = parse_serato_crate_bytes((subcrates / str(receipt["filename"])).read_bytes())
    assert len(child.paths) == preview["trackCount"]
    assert receipt["parentsCreated"] == ["XfinAudio"]
    assert receipt["validated"] is True
    assert _crate_names(subcrates) == sorted(["XfinAudio.crate", str(receipt["filename"])])


def test_a_commit_creates_the_ancestors_outermost_first_and_reports_them(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _metadata_fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name="XfinAudio%%Metadata%%Pendientes")

    receipt = _commit(backend, preview)

    created = receipt["parentsCreated"]
    assert created == ["XfinAudio", "XfinAudio%%Metadata"]
    assert _crate_names(subcrates) == [
        "XfinAudio%%Metadata%%Pendientes.crate",
        "XfinAudio%%Metadata.crate",
        "XfinAudio.crate",
    ]
    assert isinstance(created, list)
    for name in created:
        parsed = parse_serato_crate_bytes((subcrates / f"{name}.crate").read_bytes())
        assert parsed.version == SERATO_CRATE_VERSION
        assert parsed.paths == ()


def test_an_existing_parent_is_neither_rewritten_nor_backed_up(tmp_path: Path) -> None:
    backend, review, destination_id, subcrates = _generated_fixture(tmp_path)
    existing = subcrates / "XfinAudio.crate"
    existing.write_bytes(b"an earlier parent crate")
    preview = _preview(backend, {"kind": "review", "reviewId": review["reviewId"]}, destination_id)

    receipt = _commit(backend, preview)

    assert receipt["parentsCreated"] == []
    assert existing.read_bytes() == b"an earlier parent crate"
    assert not existing.with_name(f"{existing.name}.bak").exists()
    assert _crate_names(subcrates) == sorted(["XfinAudio.crate", str(receipt["filename"])])


def test_a_parent_created_between_preview_and_commit_is_left_alone(tmp_path: Path) -> None:
    backend, review, destination_id, subcrates = _generated_fixture(tmp_path)
    preview = _preview(backend, {"kind": "review", "reviewId": review["reviewId"]}, destination_id)
    assert preview["parentsToCreate"] == ["XfinAudio"]
    arrived = subcrates / "XfinAudio.crate"
    arrived.write_bytes(b"created by someone else meanwhile")

    receipt = _commit(backend, preview)

    assert receipt["parentsCreated"] == []
    assert arrived.read_bytes() == b"created by someone else meanwhile"
    assert sorted(_crate_names(subcrates)) == sorted(["XfinAudio.crate", str(receipt["filename"])])


def test_a_failed_child_removes_only_the_parents_this_commit_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, source, destination_id, subcrates = _metadata_fixture(tmp_path)
    existing = subcrates / "XfinAudio.crate"
    existing.write_bytes(b"an earlier parent crate")
    preview = _preview(backend, source, destination_id, name="XfinAudio%%Metadata%%Pendientes")
    assert preview["parentsToCreate"] == ["XfinAudio%%Metadata"]
    monkeypatch.setattr(
        serato_export_module,
        "validate_serato_round_trip",
        lambda plan, *, volume_root=None: DjReadinessCheck(
            label="Verificación Serato", status="blocked", detail="forced post-write validation failure"
        ),
    )

    with pytest.raises(BackendError) as failure:
        _commit(backend, preview)

    assert failure.value.code == "export_failed"
    # The parent this commit created is gone; the one that was already there stays byte for byte.
    assert _crate_names(subcrates) == ["XfinAudio.crate"]
    assert existing.read_bytes() == b"an earlier parent crate"


def test_a_parent_that_is_a_symlink_is_refused_like_the_child(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _metadata_fixture(tmp_path)
    elsewhere = tmp_path / "elsewhere.crate"
    elsewhere.write_bytes(build_serato_crate_bytes(()))
    (subcrates / "XfinAudio.crate").symlink_to(elsewhere)

    with pytest.raises(BackendError) as failure:
        _preview(backend, source, destination_id, name="XfinAudio%%Metadata%%Pendientes")

    assert failure.value.code == "invalid_destination"
    assert elsewhere.read_bytes() == build_serato_crate_bytes(())
    assert _crate_names(subcrates) == ["XfinAudio.crate"]


def test_a_parent_that_would_leave_subcrates_is_refused(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _metadata_fixture(tmp_path)
    serato = subcrates.parent

    with pytest.raises(BackendError) as failure:
        # A separator inside an ancestor name would place the parent outside Subcrates.
        _preview(backend, source, destination_id, name="XfinAudio%%../escape")

    assert failure.value.code == "invalid_params"
    assert _crate_names(subcrates) == []
    assert sorted(path.name for path in serato.iterdir()) == ["Subcrates"]


def test_a_name_already_nested_is_not_doubled_and_reuses_the_parent_it_created(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _metadata_fixture(tmp_path)
    preview = _preview(backend, source, destination_id, name="XfinAudio%%Reparación de BPM")

    receipt = _commit(backend, preview)

    # A name that already carries the parent prefix is kept exactly as it is.
    assert preview["filename"] == "XfinAudio%%Reparación de BPM.crate"
    assert receipt["parentsCreated"] == ["XfinAudio"]
    assert _crate_names(subcrates) == ["XfinAudio%%Reparación de BPM.crate", "XfinAudio.crate"]

    # The second export of the same name finds the parent already there.
    again = _preview(backend, source, destination_id, name="XfinAudio%%Reparación de BPM")

    assert again["filename"] == "XfinAudio%%Reparación de BPM.crate"
    assert again["parentsToCreate"] == []


def _saved_playlist_fixture(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, object], str, Path]:
    """A scanned library, one saved playlist named «22 nov» and a registered destination."""
    backend, review, destination_id, subcrates = _generated_fixture(tmp_path)
    saved = backend.execute("playlist.save", {"reviewId": review["reviewId"], "name": "22 nov"})
    return backend, {"kind": "saved", "playlistId": saved["id"]}, destination_id, subcrates


def test_a_saved_playlist_export_lives_under_the_xfinaudio_parent_crate(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _saved_playlist_fixture(tmp_path)

    preview = _preview(backend, source, destination_id, name="22 nov")

    # The saved name is used as it is, under the one XfinAudio parent crate.
    assert preview["filename"] == "XfinAudio%%22 nov.crate"
    assert preview["parentsToCreate"] == ["XfinAudio"]
    assert _crate_names(subcrates) == []

    receipt = _commit(backend, preview)

    assert receipt["filename"] == "XfinAudio%%22 nov.crate"
    assert receipt["parentsCreated"] == ["XfinAudio"]
    assert receipt["validated"] is True
    assert _crate_names(subcrates) == ["XfinAudio%%22 nov.crate", "XfinAudio.crate"]
    parent = parse_serato_crate_bytes((subcrates / "XfinAudio.crate").read_bytes())
    assert parent.paths == ()
    child = parse_serato_crate_bytes((subcrates / "XfinAudio%%22 nov.crate").read_bytes())
    assert len(child.paths) == preview["trackCount"]
    resolved = backend.execute("serato.receipt.resolve", {"receiptId": receipt["receiptId"]})
    assert resolved["path"] == str(subcrates / "XfinAudio%%22 nov.crate")


def test_a_crate_the_dj_keeps_at_the_serato_root_is_never_touched(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _saved_playlist_fixture(tmp_path)
    root_crate = subcrates / "22 nov.crate"
    root_crate.write_bytes(b"a crate the DJ made at the Serato root")
    existing_parent = subcrates / "XfinAudio.crate"
    existing_parent.write_bytes(b"an earlier parent crate")

    receipt = _commit(backend, _preview(backend, source, destination_id, name="22 nov"))

    # The export writes its own nested crate and leaves the root crate and the parent alone.
    assert receipt["filename"] == "XfinAudio%%22 nov.crate"
    assert receipt["parentsCreated"] == []
    assert root_crate.read_bytes() == b"a crate the DJ made at the Serato root"
    assert existing_parent.read_bytes() == b"an earlier parent crate"
    assert not root_crate.with_name(f"{root_crate.name}.bak").exists()
    assert _crate_names(subcrates) == ["22 nov.crate", "XfinAudio%%22 nov.crate", "XfinAudio.crate"]


def test_re_exporting_a_saved_playlist_replaces_its_crate_and_keeps_a_backup(tmp_path: Path) -> None:
    backend, source, destination_id, subcrates = _saved_playlist_fixture(tmp_path)
    first = _commit(backend, _preview(backend, source, destination_id, name="22 nov"))
    assert first["backupCreated"] is False
    before = (subcrates / "XfinAudio%%22 nov.crate").read_bytes()

    second_preview = _preview(backend, source, destination_id, name="22 nov")

    assert second_preview["filename"] == "XfinAudio%%22 nov.crate"
    assert second_preview["backup"] == {"required": True}

    second = _commit(backend, second_preview)

    # The exact name is replaced, with a backup copy of the crate it replaced.
    assert second["backupCreated"] is True
    assert second["parentsCreated"] == []
    assert (subcrates / "XfinAudio%%22 nov.crate.bak").read_bytes() == before
    assert _crate_names(subcrates) == [
        "XfinAudio%%22 nov.crate",
        "XfinAudio%%22 nov.crate.bak",
        "XfinAudio.crate",
    ]
