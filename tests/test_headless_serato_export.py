"""A Serato destination id belongs to one core process (seed flow, S8).

The renderer only holds opaque ids issued by the running core. When that process
restarts — a crash, a timeout or a supervised restart — an id from the previous
process is *unknown*, which is a different situation from a destination that
exists but can no longer be used safely. The shell needs to tell them apart so
that "detect the folder again" never becomes "ask the user for a folder".
"""

from __future__ import annotations

from datetime import datetime
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


MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _generated_fixture(tmp_path: Path) -> tuple[HeadlessBackend, dict[str, str], str, Path]:
    """A scanned library, one generated review and a registered destination on the same volume."""
    music = tmp_path / "music"
    for index in range(3):
        tagged_flac(music / f"{index}.flac", index)
    serato = tmp_path / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    review = backend.execute("prep.generate", {"targetTrackCount": 2})
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    return backend, review, destination["destinationId"], serato


def _short_name_candidates(backend: HeadlessBackend, before: datetime, after: datetime) -> set[str]:
    """The short name is «XfinAudio%%<strategy> <day>-<month>»; a midnight run may use either day."""
    assert backend.review is not None
    strategy = backend.review.recommendation.strategy.display_name
    dates = {f"{moment.day}-{MONTHS[moment.month - 1]}" for moment in (before, after)}
    return {f"XfinAudio%%{strategy} {short_date}.crate" for short_date in dates}


def test_a_generated_set_preview_proposes_the_short_style_and_date_name(tmp_path: Path) -> None:
    backend, review, destination_id, _serato = _generated_fixture(tmp_path)
    before = datetime.now()

    preview = backend.execute(
        "serato.preview",
        {"source": {"kind": "review", "reviewId": review["reviewId"]}, "destinationId": destination_id},
    )

    assert preview["filename"] in _short_name_candidates(backend, before, datetime.now())


def test_an_empty_name_leaves_the_generated_name_to_the_core(tmp_path: Path) -> None:
    backend, review, destination_id, _serato = _generated_fixture(tmp_path)
    before = datetime.now()

    preview = backend.execute(
        "serato.preview",
        {"source": {"kind": "review", "reviewId": review["reviewId"]}, "destinationId": destination_id, "name": ""},
    )

    assert preview["filename"] in _short_name_candidates(backend, before, datetime.now())


def test_a_name_the_user_typed_reaches_the_preview_unchanged(tmp_path: Path) -> None:
    backend, review, destination_id, _serato = _generated_fixture(tmp_path)

    preview = backend.execute(
        "serato.preview",
        {
            "source": {"kind": "review", "reviewId": review["reviewId"]},
            "destinationId": destination_id,
            "name": "Sábado 14-nov",
        },
    )

    assert preview["filename"] == "Sábado 14-nov.crate"
