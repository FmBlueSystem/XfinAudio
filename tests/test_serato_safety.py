"""The Serato destination binds the folder the user authorized, not the crate folder Serato rewrites (S12).

Registration records the identity of the folder the user granted — the volume and the
`_Serato_` folder — and every later preview, confirmation, commit and receipt compares it
again, opening each component without following a symlink. `Subcrates` is the one folder
inside it that Serato itself replaces: whenever Serato rewrites its crates it comes back as
a new directory with new inode numbers, while `_Serato_` and the volume keep theirs. Binding
that leaf refused the folder the user had just authorized, so the leaf is proven
structurally instead — a real directory opened below `_Serato_` without following a symlink,
on the same volume.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from xfinaudio.headless.serato_safety import (
    destination_identity,
    directory_identity,
    open_destination,
)


def _serato_folder(tmp_path: Path) -> Path:
    """A `_Serato_` folder holding a crate, as Serato and XfinAudio leave it."""
    serato = tmp_path / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    (subcrates / "Sesión equilibrada.crate").write_bytes(b"crate")
    return serato


def _rewritten_by_serato(serato: Path) -> None:
    """Rewrite the crate folder the way Serato does: the folder and its crates come back new.

    Observed on the user's drive: after Serato DJ Pro rewrites its crates, `Subcrates` and
    every crate in it carry a new inode and birth time while `_Serato_` keeps its own.
    """
    subcrates = serato / "Subcrates"
    contents = {path.name: path.read_bytes() for path in subcrates.iterdir()}
    replaced = serato / "Subcrates-replacing"
    subcrates.rename(replaced)
    subcrates.mkdir()
    for name, data in contents.items():
        (subcrates / name).write_bytes(data)
    shutil.rmtree(replaced)


def test_a_crate_folder_rewritten_by_serato_keeps_the_destination_identity(tmp_path: Path) -> None:
    serato = _serato_folder(tmp_path)
    before = destination_identity(serato)
    before_leaf = directory_identity(serato / "Subcrates")[-1]

    _rewritten_by_serato(serato)

    assert directory_identity(serato / "Subcrates")[-1] != before_leaf  # the leaf is a new directory
    assert destination_identity(serato) == before


def test_a_replaced_serato_folder_changes_the_destination_identity(tmp_path: Path) -> None:
    serato = _serato_folder(tmp_path)
    before = destination_identity(serato)

    shutil.move(str(serato), str(tmp_path / "_Serato_-old"))
    serato.mkdir()
    shutil.move(str(tmp_path / "_Serato_-old" / "Subcrates"), str(serato / "Subcrates"))

    assert destination_identity(serato) != before


def test_the_crate_folder_must_live_on_the_destination_volume(tmp_path: Path) -> None:
    serato = _serato_folder(tmp_path)
    with open_destination(serato) as (_descriptor, lineage, folder_device):
        assert folder_device == lineage[-1][0]


def test_a_crate_folder_swapped_for_a_symlink_is_refused(tmp_path: Path) -> None:
    serato = _serato_folder(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    shutil.rmtree(serato / "Subcrates")
    (serato / "Subcrates").symlink_to(elsewhere)

    with pytest.raises(OSError):
        destination_identity(serato)


def test_a_crate_folder_replaced_by_a_regular_file_is_refused(tmp_path: Path) -> None:
    serato = _serato_folder(tmp_path)
    shutil.rmtree(serato / "Subcrates")
    (serato / "Subcrates").write_bytes(b"not a folder")

    with pytest.raises(OSError):
        destination_identity(serato)


def test_a_serato_folder_swapped_for_a_symlink_is_refused(tmp_path: Path) -> None:
    serato = _serato_folder(tmp_path)
    elsewhere = tmp_path / "elsewhere" / "_Serato_"
    elsewhere.mkdir(parents=True)
    (elsewhere / "Subcrates").mkdir()
    shutil.move(str(serato / "Subcrates"), str(elsewhere / "Subcrates"))
    shutil.rmtree(serato)
    serato.symlink_to(elsewhere, target_is_directory=True)

    with pytest.raises(OSError):
        destination_identity(serato)


def test_a_missing_crate_folder_is_refused(tmp_path: Path) -> None:
    serato = _serato_folder(tmp_path)
    shutil.rmtree(serato / "Subcrates")

    with pytest.raises(OSError):
        destination_identity(serato)
