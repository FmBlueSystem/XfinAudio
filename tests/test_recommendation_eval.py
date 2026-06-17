"""Tests for the read-only recommendation evaluation harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.recommendation.evaluation import (
    EvalConfig,
    EvalReport,
    StrategyMetrics,
    _cross_genre_fraction,
    _energy_monotonic_fraction,
    _fill_rate,
    _sample_anchors,
    _transition_valid,
    evaluate_recommendations,
)


def _track(
    path: str,
    *,
    bpm: float = 124.0,
    camelot_key: str = "8A",
    energy_level: int = 5,
    genre: str | None = "house",
    tags: list[str] | None = None,
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        artist="a",
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        genre=genre,
        tags=tags or [],
        metadata_status="complete",
    )


# R4 — hard-rule transition validity oracle


def test_transition_valid_same_key_and_bpm() -> None:
    assert _transition_valid(_track("a", camelot_key="8A", bpm=124.0), _track("b", camelot_key="8A", bpm=125.0))


def test_transition_valid_adjacent_number_same_letter() -> None:
    assert _transition_valid(_track("a", camelot_key="8A"), _track("b", camelot_key="9A"))


def test_transition_valid_wraps_around_wheel() -> None:
    assert _transition_valid(_track("a", camelot_key="12A"), _track("b", camelot_key="1A"))


def test_transition_valid_relative_major_minor() -> None:
    assert _transition_valid(_track("a", camelot_key="8A"), _track("b", camelot_key="8B"))


def test_cross_genre_fraction_counts_disjoint_genre_adjacencies() -> None:
    ordered = [
        _track("a", genre="House, Disco"),
        _track("b", genre="House, Funk"),  # shares 'house' -> not cross
        _track("c", genre="Techno"),  # disjoint from House,Funk -> cross
        _track("d", genre="Techno"),  # shares 'techno' -> not cross
    ]
    # 3 adjacencies, 1 cross-genre.
    assert _cross_genre_fraction(ordered) == pytest.approx(1 / 3)


def test_cross_genre_fraction_ignores_missing_genre() -> None:
    ordered = [_track("a", genre=None), _track("b", genre="Techno")]
    assert _cross_genre_fraction(ordered) == 0.0


def test_transition_invalid_distant_key() -> None:
    assert not _transition_valid(_track("a", camelot_key="8A"), _track("b", camelot_key="3B"))


def test_transition_invalid_bpm_jump_over_three_percent() -> None:
    assert not _transition_valid(_track("a", bpm=120.0), _track("b", bpm=130.0))


def test_transition_invalid_when_metadata_missing() -> None:
    left = _track("a")
    right = TrackRecord(path="b", metadata_status="complete", camelot_key=None, bpm=None)
    assert not _transition_valid(left, right)


# R3 — fill rate


def test_fill_rate_is_ratio_clamped_to_one() -> None:
    assert _fill_rate(1, 25) == 1 / 25
    assert _fill_rate(30, 25) == 1.0
    assert _fill_rate(0, 25) == 0.0


# R5 — energy monotonicity


def test_energy_monotonic_fraction_all_ascending() -> None:
    tracks = [_track("a", energy_level=1), _track("b", energy_level=3), _track("c", energy_level=5)]
    assert _energy_monotonic_fraction(tracks) == 1.0


def test_energy_monotonic_fraction_partial() -> None:
    tracks = [_track("a", energy_level=5), _track("b", energy_level=3), _track("c", energy_level=4)]
    assert _energy_monotonic_fraction(tracks) == 0.5


# R2 — deterministic sampling


def test_sample_anchors_is_deterministic_for_seed() -> None:
    tracks = [_track(f"t{i}", bpm=120.0 + i) for i in range(20)]
    first = _sample_anchors(tracks, seed=7, n=5)
    second = _sample_anchors(tracks, seed=7, n=5)
    assert [t.path for t in first] == [t.path for t in second]
    assert len(first) == 5


def test_sample_anchors_caps_at_population() -> None:
    tracks = [_track(f"t{i}") for i in range(3)]
    assert len(_sample_anchors(tracks, seed=1, n=10)) == 3


# R3/R4/R5/R6 — orchestration


def _library() -> list[TrackRecord]:
    library: list[TrackRecord] = []
    for i in range(15):
        library.append(
            _track(
                f"track-{i}",
                bpm=124.0 + (i % 3),
                camelot_key="8A" if i % 2 == 0 else "9A",
                energy_level=1 + (i % 9),
                genre="house",
                tags=["dark"] if i % 2 == 0 else ["warm"],
            )
        )
    return library


def test_evaluate_recommendations_returns_report_per_strategy() -> None:
    config = EvalConfig(
        seed=11,
        sample_size=3,
        requested_size=10,
        candidate_limit=25,
        strategies=("harmonic_journey", "warmup"),
    )
    report = evaluate_recommendations(_library(), config)
    assert isinstance(report, EvalReport)
    assert {m.strategy for m in report.strategies} == {"harmonic_journey", "warmup"}
    for metrics in report.strategies:
        assert isinstance(metrics, StrategyMetrics)
        assert metrics.samples > 0
        assert 0.0 <= metrics.mean_fill_rate <= 1.0
        assert 0.0 <= metrics.mean_transition_validity <= 1.0


def test_evaluate_recommendations_monotonicity_only_for_directional() -> None:
    config = EvalConfig(
        seed=11,
        sample_size=2,
        requested_size=8,
        candidate_limit=25,
        strategies=("harmonic_journey", "warmup"),
    )
    report = evaluate_recommendations(_library(), config)
    by_name = {m.strategy: m for m in report.strategies}
    assert by_name["harmonic_journey"].mean_energy_monotonicity is None
    assert by_name["warmup"].mean_energy_monotonicity is not None


def test_report_render_is_deterministic() -> None:
    config = EvalConfig(
        seed=3,
        sample_size=2,
        requested_size=8,
        candidate_limit=25,
        strategies=("harmonic_journey",),
    )
    library = _library()
    first = evaluate_recommendations(library, config).render()
    second = evaluate_recommendations(library, config).render()
    assert first == second
    assert "harmonic_journey" in first


# Task 10 — CLI smoke


def _load_cli_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "eval_recommendation.py"
    spec = importlib.util.spec_from_file_location("eval_recommendation_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_runs_read_only_against_temp_db(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db_path = tmp_path / "lib.sqlite3"
    repo = TrackRepository(db_path)
    repo.save_scan_results(_library())

    cli = _load_cli_module()
    exit_code = cli.main(
        [
            "--db",
            str(db_path),
            "--seed",
            "5",
            "--sample-size",
            "3",
            "--requested-size",
            "8",
            "--strategies",
            "harmonic_journey",
        ]
    )

    assert exit_code == 0
    assert "harmonic_journey" in capsys.readouterr().out
