"""Serato destination registration keeps its canonical `_Serato_` contract.

The manual picker accepts a parent folder (the drive root, `~/Music`) and
resolves the `_Serato_` folder inside it in the trusted host process, so
registration keeps exactly the checks it always had: a canonical existing
folder named `_Serato_` that contains `Subcrates/`.
"""

from pathlib import Path

import pytest

from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError


def _backend(tmp_path: Path) -> HeadlessBackend:
    return HeadlessBackend(tmp_path / "data")


def test_registers_a_canonical_serato_folder_containing_subcrates(tmp_path: Path) -> None:
    serato = tmp_path / "dd" / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)

    result = _backend(tmp_path).execute("serato.registerDestination", {"seratoRoot": str(serato)})

    assert result["label"].startswith("_Serato_ · ")
    assert result["destinationId"]


def test_a_parent_folder_is_still_refused_registration_it_must_be_resolved_first(tmp_path: Path) -> None:
    serato = tmp_path / "dd" / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)

    with pytest.raises(BackendError) as failure:
        _backend(tmp_path).execute("serato.registerDestination", {"seratoRoot": str(tmp_path / "dd")})

    assert failure.value.code == "invalid_destination"


def test_a_folder_without_subcrates_is_still_refused(tmp_path: Path) -> None:
    serato = tmp_path / "dd" / "_Serato_"
    serato.mkdir(parents=True)

    with pytest.raises(BackendError) as failure:
        _backend(tmp_path).execute("serato.registerDestination", {"seratoRoot": str(serato)})

    assert failure.value.code == "invalid_destination"
