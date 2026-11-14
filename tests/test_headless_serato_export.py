"""A Serato destination id belongs to one core process (seed flow, S8).

The renderer only holds opaque ids issued by the running core. When that process
restarts — a crash, a timeout or a supervised restart — an id from the previous
process is *unknown*, which is a different situation from a destination that
exists but can no longer be used safely. The shell needs to tell them apart so
that "detect the folder again" never becomes "ask the user for a folder".
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mutagen.flac import FLAC

from tests.test_headless_backend import tagged_flac
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_export import SeratoExporter


def _fixture(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, object], dict[str, str], Path]:
    music = tmp_path / "music"
    for index in range(2):
        tagged_flac(music / f"{index}.flac", index)
    for index in (0, 1):
        tags = FLAC(music / f"{index}.flac")
        del tags["bpm"]
        tags.save()
    serato = tmp_path / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)
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
    return backend, source, destination, serato


def test_a_destination_id_from_a_previous_core_is_unknown(tmp_path: Path) -> None:
    backend, source, destination, _serato = _fixture(tmp_path)
    # A restart keeps the data directory and loses only the process memory.
    restarted = SeratoExporter(backend)

    with pytest.raises(BackendError) as failure:
        restarted.execute(
            "serato.preview",
            {"source": source, "destinationId": destination["destinationId"], "name": "Warmup"},
        )

    assert failure.value.code == "unknown_destination"
    assert not restarted.previews


def test_the_same_core_still_previews_its_own_destination(tmp_path: Path) -> None:
    backend, source, destination, _serato = _fixture(tmp_path)

    preview = backend.execute(
        "serato.preview",
        {"source": source, "destinationId": destination["destinationId"], "name": "Warmup"},
    )

    assert preview["previewId"]
    assert preview["destinationLabel"] == destination["label"]


def test_a_destination_whose_folder_changed_keeps_the_invalid_destination_refusal(tmp_path: Path) -> None:
    backend, source, destination, serato = _fixture(tmp_path)
    (serato / "Subcrates").rename(serato / "Subcrates-replaced")
    (serato / "Subcrates").mkdir()

    with pytest.raises(BackendError) as failure:
        backend.execute(
            "serato.preview",
            {"source": source, "destinationId": destination["destinationId"], "name": "Warmup"},
        )

    assert failure.value.code == "invalid_destination"
