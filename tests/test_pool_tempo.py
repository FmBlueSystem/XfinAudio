"""S1 — tempo-coherent candidate pools for generation without control tracks."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.candidate_pool import build_recommendation_pool
from xfinaudio.recommendation.controls import DJControls


def record(path: str, bpm: float | None, *, energy_level: int = 5) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path.rsplit("/", 1)[-1],
        artist="Artist",
        bpm=bpm,
        camelot_key="8A",
        energy_level=energy_level,
        duration=240.0,
        genre="House",
        tags=["house"],
        metadata_status="complete",
    )


@pytest.mark.parametrize("spread_energy", [False, True])
def test_no_control_pool_uses_densest_tempo_window_interleaved_by_energy(spread_energy: bool) -> None:
    cluster = [
        record("/cluster-00.flac", 124.0, energy_level=3),
        record("/cluster-01.flac", 128.0, energy_level=7),
        record("/cluster-02.flac", 126.0, energy_level=5),
        record("/cluster-03.flac", 124.0, energy_level=3),
        record("/cluster-04.flac", 128.0, energy_level=7),
        record("/cluster-05.flac", 126.0, energy_level=5),
        record("/cluster-06.flac", 124.0, energy_level=3),
        record("/cluster-07.flac", 128.0, energy_level=7),
        record("/cluster-08.flac", 126.0, energy_level=5),
    ]
    scattered = [
        record("/scattered-90.flac", 90.0),
        record("/scattered-150.flac", 150.0),
        record("/scattered-170.flac", 170.0),
    ]

    pool = build_recommendation_pool(
        [*scattered, *cluster],
        DJControls(),
        limit=6,
        spread_energy=spread_energy,
    )

    assert [track.path for track in pool] == [
        "/cluster-00.flac",
        "/cluster-02.flac",
        "/cluster-01.flac",
        "/cluster-03.flac",
        "/cluster-05.flac",
        "/cluster-04.flac",
    ]


def test_equal_tempo_clusters_choose_the_lower_bpm() -> None:
    high = [record(f"/high-{index}.flac", 140.0 + index) for index in range(3)]
    low = [record(f"/low-{index}.flac", 100.0 + index) for index in range(3)]

    pool = build_recommendation_pool([*high, *low], DJControls(), limit=3)

    assert [track.path for track in pool] == [track.path for track in low]


def test_short_tempo_window_is_filled_by_the_nearest_outside_bpm() -> None:
    window = [record(f"/window-{index}.flac", 120.0) for index in range(4)]
    far = record("/far.flac", 160.0)
    middle = record("/middle.flac", 100.0)
    near = record("/near.flac", 110.0)

    pool = build_recommendation_pool(
        [far, window[0], middle, window[1], near, window[2], window[3]],
        DJControls(),
        limit=7,
    )

    assert [track.path for track in pool] == [
        *[track.path for track in window],
        near.path,
        middle.path,
        far.path,
    ]


@pytest.mark.parametrize("control", ["start", "end", "required"])
def test_control_track_pool_keeps_its_existing_order(control: str) -> None:
    anchor = record("/anchor.flac", 120.0)
    near = [
        record("/near-119.flac", 119.0),
        record("/near-121.flac", 121.0),
        record("/near-122.flac", 122.0),
    ]
    far = [record("/far-150.flac", 150.0), record("/far-90.flac", 90.0)]
    controls = {
        "start": DJControls(start_path=anchor.path),
        "end": DJControls(end_path=anchor.path),
        "required": DJControls(manual_order_paths=[anchor.path]),
    }[control]

    pool = build_recommendation_pool([anchor, *near, *far], controls, limit=6, spread_energy=True)

    assert [track.path for track in pool] == [
        anchor.path,
        *[track.path for track in near],
        "/far-150.flac",
        "/far-90.flac",
    ]


def test_full_prep_generate_reaches_twenty_tracks_without_a_control_track(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 60)
    scattered_bpms = [70.0 + index for index in range(15)] + [180.0 + 4 * index for index in range(15)]
    cluster_bpms = [124.0 + index % 5 for index in range(30)]
    updated = [
        source.model_copy(update={"bpm": bpm})
        for source, bpm in zip(records, [*scattered_bpms, *cluster_bpms], strict=True)
    ]
    backend.repository.save_scan_results(updated)

    result = backend.execute("prep.generate", {"targetTrackCount": 20, "name": "Tempo"})

    assert len(result["tracks"]) == 20
    cluster_ids = {identity(track) for track in updated[30:]}
    assert {track["id"] for track in result["tracks"]} <= cluster_ids
