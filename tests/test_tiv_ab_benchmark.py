"""Tests for the TIV A/B benchmark.

The comparison logic is exercised on synthetic in-memory records (no database,
no audio); the guard test mirrors the arc subset benchmark so the tool can never
read or mutate the live application database.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from xfinaudio.audio.tonal_profile import TonalProfile
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "tiv_ab_benchmark.py"

_benchmark_spec = importlib.util.spec_from_file_location("tiv_ab_benchmark", BENCHMARK_SCRIPT_PATH)
assert _benchmark_spec is not None
assert _benchmark_spec.loader is not None
tiv_ab_benchmark = importlib.util.module_from_spec(_benchmark_spec)
# Register before exec so @dataclass can resolve the module namespace; the arc
# benchmark test skips this only because it defines no dataclasses.
sys.modules[_benchmark_spec.name] = tiv_ab_benchmark
_benchmark_spec.loader.exec_module(tiv_ab_benchmark)


class _StubRepository:
    """Repository stand-in that never touches the database file."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def list_tracks(self) -> list[object]:
        return []


def _record(
    title: str,
    key: str,
    bpm: float,
    energy: int,
    tiv: tuple[float, float, float, float, float, float],
) -> TrackRecord:
    return TrackRecord(
        path=f"/{title}.flac",
        title=title,
        camelot_key=key,
        bpm=bpm,
        energy_level=energy,
        metadata_status="complete",
        tonal_profile=TonalProfile(tiv=tiv, tonal_coherence=0.5),
    )


def _synthetic_library() -> list[TrackRecord]:
    return [
        _record("alpha", "8A", 124.0, 5, (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
        _record("bravo", "8A", 125.0, 5, (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
        _record("charlie", "9A", 126.0, 6, (0.0, 1.0, 0.0, 0.0, 0.0, 0.0)),
        _record("delta", "1A", 128.0, 7, (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)),
        _record("echo", "2A", 130.0, 8, (0.0, 0.0, 0.0, 1.0, 0.0, 0.0)),
        _record("foxtrot", "7A", 122.0, 4, (0.0, 0.0, 0.0, 0.0, 1.0, 0.0)),
    ]


def test_differing_positions_reports_every_index_that_changes() -> None:
    assert tiv_ab_benchmark.differing_positions(["a", "b", "c"], ["a", "c", "b"]) == [1, 2]


def test_differing_positions_handles_different_lengths() -> None:
    assert tiv_ab_benchmark.differing_positions(["a", "b"], ["a", "b", "c"]) == [2]
    assert tiv_ab_benchmark.differing_positions(["a", "b", "c"], ["a", "b"]) == [2]
    assert tiv_ab_benchmark.differing_positions(["a"], ["a"]) == []


def test_arm_weights_override_only_the_tonal_component() -> None:
    base = tiv_ab_benchmark.arm_weights("harmonic_journey", 0.0)
    enabled = tiv_ab_benchmark.arm_weights("harmonic_journey", 0.25)

    assert base.tonal == 0.0
    assert enabled.tonal == 0.25
    assert enabled.harmonic == base.harmonic
    assert enabled.model_copy(update={"tonal": 0.0}) == base


def test_build_comparison_reports_orders_totals_and_tonal_components() -> None:
    tracks = _synthetic_library()
    anchor = tracks[0].path
    default = tiv_ab_benchmark.run_arm(tracks, "harmonic_journey", anchor, 0.0, len(tracks))
    enabled = tiv_ab_benchmark.run_arm(tracks, "harmonic_journey", anchor, 0.3, len(tracks))

    comparison = tiv_ab_benchmark.build_comparison("harmonic_journey", anchor, default, enabled)

    assert comparison.intent == "harmonic_journey"
    assert comparison.anchor_path == anchor
    assert comparison.default_order == tuple(track.path for track in default.ordered_tracks)
    assert comparison.tonal_order == tuple(track.path for track in enabled.ordered_tracks)
    assert comparison.differing_positions == tuple(
        tiv_ab_benchmark.differing_positions(list(comparison.default_order), list(comparison.tonal_order))
    )
    assert comparison.default_total == default.total_score
    assert comparison.tonal_total == enabled.total_score
    assert len(comparison.default_tonal_components) == max(len(default.ordered_tracks) - 1, 0)
    assert len(comparison.tonal_tonal_components) == max(len(enabled.ordered_tracks) - 1, 0)


def test_tonal_arm_override_enables_the_tonal_component() -> None:
    tracks = _synthetic_library()

    enabled = tiv_ab_benchmark.run_arm(tracks, "harmonic_journey", tracks[0].path, 0.3, len(tracks))

    assert any(score.component_scores.get("tonal") is not None for score in enabled.transition_scores)


def test_tonal_components_lists_per_transition_values() -> None:
    tracks = _synthetic_library()
    enabled = tiv_ab_benchmark.run_arm(tracks, "harmonic_journey", tracks[0].path, 0.3, len(tracks))

    components = tiv_ab_benchmark.tonal_components(enabled)

    assert components == [score.component_scores.get("tonal") for score in enabled.transition_scores]


def test_select_anchors_is_deterministic_and_bounded() -> None:
    tracks = _synthetic_library()

    anchors = tiv_ab_benchmark.select_anchors(tracks, 3)

    assert anchors == tiv_ab_benchmark.select_anchors(tracks, 3)
    assert len(anchors) == 3
    assert all(anchor in tracks for anchor in anchors)


def test_main_refuses_a_hard_link_to_the_live_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    live = home / ".xfinaudio" / "xfinaudio.sqlite3"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"stand-in for the live application database")
    hard_link = tmp_path / "scratch.sqlite3"
    os.link(live, hard_link)

    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(tiv_ab_benchmark, "TrackRepository", _StubRepository)

    assert tiv_ab_benchmark.main(["--db", str(hard_link)]) == 2
    assert "refusing to read the live database" in capsys.readouterr().err


def test_main_rejects_a_missing_database(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "nope.sqlite3"

    assert tiv_ab_benchmark.main(["--db", str(missing)]) == 2
    assert "database not found" in capsys.readouterr().err


def test_main_runs_both_arms_over_a_scratch_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    db_path = tmp_path / "scratch.sqlite3"
    TrackRepository(db_path).save_scan_results(_synthetic_library())

    exit_code = tiv_ab_benchmark.main(["--db", str(db_path), "--anchors", "1", "--target-count", "3", "--verbose"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "library: 6 tracks, 6 complete" in out
    assert "tonal arm weight: 0.2" in out
    assert "harmonic_journey" in out
    assert "per-transition tonal components" in out
