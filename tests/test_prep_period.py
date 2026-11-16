"""S16: the Prep form's optional release period narrows the generated candidates."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.test_headless_prep_parity import identity
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan

# One track per real release year shape: a decade corner, an unknown year and tracks
# outside the period so a filter that does nothing is visible.
YEARS = (1970, 1985, 1986, None, 1990, 1987, 2020, 1988)
IN_1980S = (1, 2, 5, 7)
CONTROLS = (0, 3, 6)


def seeded(tmp_path: Path) -> tuple[HeadlessBackend, list[TrackRecord]]:
    root = tmp_path / "music"
    root.mkdir()
    records = [
        TrackRecord(
            path=str(root / f"{index:03}.flac"),
            title=f"Track {index}",
            artist="Artist",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            duration=240,
            genre="House",
            metadata_status="complete",
            release_year=year,
        )
        for index, year in enumerate(YEARS)
    ]
    for record in records:
        Path(record.path).touch()
    backend = HeadlessBackend(tmp_path / "data")
    backend.roots = [root]
    backend.repository.save_scan_results(records)
    return backend, records


def test_a_generation_with_a_period_keeps_only_in_period_tracks_plus_the_chosen_controls(
    tmp_path: Path,
) -> None:
    backend, records = seeded(tmp_path)
    result = backend.execute(
        "prep.generate",
        {
            "targetTrackCount": 7,
            "name": "Ochenta",
            "startTrackId": identity(records[0]),
            "endTrackId": identity(records[3]),
            "requiredTrackIds": [identity(records[6])],
            "yearMin": 1980,
            "yearMax": 1989,
        },
    )
    ids = [track["id"] for track in result["tracks"]]
    allowed = {identity(records[index]) for index in (*IN_1980S, *CONTROLS)}
    assert set(ids) <= allowed
    # The chosen opening is outside the period and is still first; the closing and the
    # required track are outside it too and are still kept.
    assert ids[0] == identity(records[0])
    assert identity(records[3]) in ids
    assert identity(records[6]) in ids
    assert backend.plan.intent.year_min == 1980
    assert backend.plan.intent.year_max == 1989


@pytest.mark.parametrize(
    ("period", "allowed_years"),
    [
        ({"yearMin": 1990}, (4, 6)),
        ({"yearMax": 1989}, (0, 1, 2, 5, 7)),
    ],
)
def test_one_year_alone_is_an_open_range(
    tmp_path: Path, period: dict[str, int], allowed_years: tuple[int, ...]
) -> None:
    backend, records = seeded(tmp_path)
    result = backend.execute("prep.generate", {"targetTrackCount": 8, "name": "Abierto", **period})
    ids = {track["id"] for track in result["tracks"]}
    assert ids
    assert ids <= {identity(records[index]) for index in allowed_years}


def test_a_request_without_a_period_plans_exactly_as_before(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path)
    params = {"targetTrackCount": 5, "name": "Sin época"}
    result = backend.execute("prep.generate", params)
    assert backend.plan.intent == DJSetIntent(name="Sin época", target_track_count=5)
    assert "yearMin" not in result and "yearMax" not in result
    plain = build_prep_copilot_plan(records, DJSetIntent(name="Sin época", target_track_count=5))
    balanced = next(item for item in plain.variants if item.name == "balanced")
    assert [track["id"] for track in result["tracks"]] == [identity(t) for t in balanced.recommendation.ordered_tracks]


def test_a_period_that_leaves_the_list_short_keeps_the_existing_notice(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    result = backend.execute(
        "prep.generate", {"targetTrackCount": 8, "name": "Corto", "yearMin": 1985, "yearMax": 1986}
    )
    assert 0 < len(result["tracks"]) < 8
    assert any("Track count shortfall" in warning for warning in result["warnings"])


@pytest.mark.parametrize(
    "change",
    [
        {"yearMin": 1899},
        {"yearMax": 2101},
        {"yearMin": "1980"},
        {"yearMin": True},
        {"yearMin": 1985.5},
        {"yearMin": 1990, "yearMax": 1980},
        {"yearMin": None},
    ],
)
def test_a_period_outside_the_form_contract_is_refused_before_generation(
    tmp_path: Path, change: dict[str, object]
) -> None:
    backend, _ = seeded(tmp_path)
    with pytest.raises(BackendError) as exc:
        backend.execute("prep.generate", {"targetTrackCount": 3, **change})
    assert exc.value.code == "invalid_params"
    assert str(tmp_path) not in str(exc.value)


def test_the_intent_refuses_a_period_that_ends_before_it_starts() -> None:
    with pytest.raises(ValidationError, match="initial year"):
        DJSetIntent(name="Club", year_min=1990, year_max=1980)
