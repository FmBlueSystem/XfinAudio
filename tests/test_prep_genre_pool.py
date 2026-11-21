"""S4: a genre focus chooses from the whole eligible library, not the capped pool."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.test_headless_prep_parity import identity
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.library.models import TrackRecord

FOCUS = "Synth Pop & New Wave"
OTHER = "House & Electronic"
TARGET = 20
PLAIN_ORDER = tuple(range(60, 80))
VARIANTS = ("safe", "balanced", "adventurous")


@pytest.fixture
def workspace() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(dir="/private/tmp", prefix="xfinaudio-s4-") as scratch:
        yield Path(scratch)


def record(
    music: Path,
    index: int,
    *,
    genre: str,
    bpm: float,
    year: int | None = None,
    tags: list[str] | None = None,
) -> TrackRecord:
    path = str(music / f"{index:03}.flac")
    Path(path).touch()
    return TrackRecord(
        path=path,
        title=f"Track {index}",
        artist="Artist",
        bpm=bpm,
        camelot_key="8A",
        energy_level=5,
        duration=240,
        genre=genre,
        tags=[genre] if tags is None else tags,
        release_year=year,
        metadata_status="complete",
    )


def seeded(root: Path, records: list[TrackRecord]) -> HeadlessBackend:
    backend = HeadlessBackend(root / "data")
    backend.roots = [root / "music"]
    backend.repository.save_scan_results(records)
    return backend


def wide_library(root: Path) -> tuple[HeadlessBackend, list[TrackRecord]]:
    """60 focused tracks in a tempo spread, behind 240 tracks in a denser tempo cluster."""
    music = root / "music"
    music.mkdir()
    records = [
        record(
            music,
            index,
            genre=FOCUS if index < 60 else OTHER,
            bpm=120.0 + index % 8 if index < 60 else 100.0,
        )
        for index in range(300)
    ]
    return seeded(root, records), records


def period_library(root: Path) -> tuple[HeadlessBackend, list[TrackRecord]]:
    """30 in-period focused tracks, 30 out-of-period ones and one protected control."""
    music = root / "music"
    music.mkdir()
    records = []
    for index in range(300):
        if index < 60:
            genre, bpm, year = FOCUS, 120.0 + index % 8, 1995 if index < 30 else 2005
        else:
            genre, bpm, year = OTHER, 120.0, 2005 if index == 299 else 1995
        records.append(record(music, index, genre=genre, bpm=bpm, year=year))
    return seeded(root, records), records


def tag_library(root: Path) -> tuple[HeadlessBackend, list[TrackRecord]]:
    """Focused genre and tag-only bridges alternate inside the first 60 tracks."""
    music = root / "music"
    music.mkdir()
    records = []
    for index in range(300):
        if index >= 60:
            genre, tags, bpm = OTHER, None, 100.0
        elif index % 2 == 0:
            genre, tags, bpm = FOCUS, None, 120.0 + index % 8
        else:
            genre, tags, bpm = OTHER, [OTHER, FOCUS], 120.0 + index % 8
        records.append(record(music, index, genre=genre, bpm=bpm, tags=tags))
    return seeded(root, records), records


def generate(backend: HeadlessBackend, **params: Any) -> dict[str, Any]:
    return backend.execute("prep.generate", {"targetTrackCount": TARGET, **params})


def select(backend: HeadlessBackend, result: dict[str, Any], name: str) -> dict[str, Any]:
    return backend.execute("prep.select", {"planId": result["planId"], "variant": name})


def indices(records: list[TrackRecord]) -> dict[str, int]:
    return {identity(record): index for index, record in enumerate(records)}


def test_safe_and_balanced_reach_the_target_from_the_whole_genre(workspace: Path) -> None:
    backend, records = wide_library(workspace)
    plain = generate(backend)
    assert sum(track["genre"] == FOCUS for track in plain["tracks"]) <= 2

    result = generate(backend, genreFocus=FOCUS)
    balanced = result["tracks"]
    safe = select(backend, result, "safe")["tracks"]

    assert result["variant"] == "balanced"
    assert len(safe) == len(balanced) == TARGET
    assert {track["genre"] for track in safe} == {FOCUS}
    assert {track["genre"] for track in balanced} == {FOCUS}
    assert {identity(record) for record in records[:60]} >= {track["id"] for track in balanced}


def test_adventurous_is_unchanged_by_a_genre_focus(workspace: Path) -> None:
    backend, _ = wide_library(workspace)
    plain = generate(backend)
    plain_adventurous = select(backend, plain, "adventurous")

    focused = generate(backend, genreFocus=FOCUS)
    focused_adventurous = select(backend, focused, "adventurous")

    assert [track["id"] for track in focused_adventurous["tracks"]] == [
        track["id"] for track in plain_adventurous["tracks"]
    ]
    assert any(track["genre"] != FOCUS for track in focused_adventurous["tracks"])
    assert any("genre focus" in warning for warning in focused_adventurous["warnings"])


def test_a_request_without_a_genre_focus_keeps_the_existing_answer(workspace: Path) -> None:
    backend, records = wide_library(workspace)
    result = generate(backend)
    by_id = indices(records)

    assert [by_id[track["id"]] for track in result["tracks"]] == list(PLAIN_ORDER)
    assert result["variant"] == "balanced"
    assert result["warnings"] == []
    assert result["blockers"] == []
    assert result["readiness"] == "ready"
    assert result["qualityScore"] == pytest.approx(0.884615)
    assert [
        (item["name"], item["trackCount"], item["readiness"], item["warnings"], item["blockers"])
        for item in result["variants"]
    ] == [(name, TARGET, "ready", [], []) for name in VARIANTS]


def test_a_period_still_applies_before_the_whole_genre_pool(workspace: Path) -> None:
    backend, records = period_library(workspace)
    control_id = identity(records[-1])
    by_id = {identity(record): record for record in records}
    result = generate(
        backend,
        genreFocus=FOCUS,
        requiredTrackIds=[control_id],
        yearMin=1990,
        yearMax=1999,
    )
    safe = select(backend, result, "safe")["tracks"]
    adventurous = select(backend, result, "adventurous")["tracks"]
    balanced = result["tracks"]

    for tracks in (safe, balanced, adventurous):
        assert len(tracks) == TARGET
        assert control_id in {track["id"] for track in tracks}
        for track in tracks:
            source = by_id[track["id"]]
            assert source.release_year == 1995 or source.path == records[-1].path
    for tracks in (safe, balanced):
        assert {track["genre"] for track in tracks if track["id"] != control_id} == {FOCUS}


def test_balanced_uses_genre_or_tag_matches_from_the_whole_library(workspace: Path) -> None:
    backend, records = tag_library(workspace)
    by_id = indices(records)
    result = generate(backend, genreFocus=FOCUS)
    balanced = result["tracks"]
    safe = select(backend, result, "safe")["tracks"]

    assert len(safe) == len(balanced) == TARGET
    assert {track["genre"] for track in safe} == {FOCUS}
    assert all(by_id[track["id"]] < 60 for track in balanced)
    assert any(by_id[track["id"]] % 2 == 1 for track in balanced)
