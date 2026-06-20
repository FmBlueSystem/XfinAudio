"""Tests for export filename generation."""

from __future__ import annotations

from datetime import datetime

from xfinaudio.exporting.export_naming import default_export_filename
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.scoring import ScoringWeights, TransitionScore
from xfinaudio.recommendation.strategies import PlaylistStrategy


def _make_recommendation(strategy_name: str = "build", track_count: int = 12) -> PlaylistRecommendation:
    """Build a minimal recommendation for filename tests."""
    tracks = [TrackRecord(path=f"/music/track_{i:02d}.mp3", title=f"Track {i}") for i in range(track_count)]
    transition_scores = []
    if len(tracks) >= 2:
        transition_scores.append(
            TransitionScore(
                left_path=tracks[0].path,
                right_path=tracks[1].path,
                total_score=0.9,
                component_scores={"harmonic": 0.9},
                explanations=["good"],
                warnings=[],
            )
        )
    return PlaylistRecommendation(
        ordered_tracks=tracks,
        transition_scores=transition_scores,
        strategy=PlaylistStrategy(
            name=strategy_name,
            display_name=strategy_name.replace("_", " ").title(),
            description="Test strategy",
            weights=ScoringWeights(),
        ),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.9,
    )


def test_default_export_filename_includes_timestamp_and_strategy() -> None:
    """The default filename contains timestamp and strategy name."""
    recommendation = _make_recommendation(strategy_name="peak_time", track_count=5)
    generated_at = datetime(2026, 6, 14, 3, 30, 45)

    name = default_export_filename(recommendation, generated_at=generated_at, suffix="rekordbox")

    assert name.startswith("20260614_033045_")
    assert "peak_time" in name


def test_default_export_filename_includes_suffix_and_track_count() -> None:
    """The filename includes the software suffix and track count."""
    recommendation = _make_recommendation(track_count=1)
    generated_at = datetime(2026, 6, 14, 3, 30, 45)

    name = default_export_filename(recommendation, generated_at=generated_at, suffix="traktor")

    assert "traktor" in name
    assert "1_track" in name
    assert "tracks" not in name or "1_track" in name


def test_default_export_filename_is_filesystem_safe() -> None:
    """Special characters and spaces are sanitized out of the filename."""
    recommendation = _make_recommendation(strategy_name="energy boost", track_count=3)
    generated_at = datetime(2026, 6, 14, 3, 30, 45)

    name = default_export_filename(recommendation, generated_at=generated_at, suffix="VirtualDJ")

    assert " " not in name
    assert "/" not in name
    assert "virtualdj" in name
    assert "energy_boost" in name


def test_default_export_filename_without_suffix() -> None:
    """Filename works without an explicit suffix."""
    recommendation = _make_recommendation(strategy_name="warmup", track_count=8)
    generated_at = datetime(2026, 6, 14, 3, 30, 45)

    name = default_export_filename(recommendation, generated_at=generated_at)

    assert "warmup" in name
    assert "8_tracks" in name


def test_default_export_filename_ignores_suffix_that_sanitizes_to_empty() -> None:
    """Unsafe-only suffix does not create an empty filename part."""
    recommendation = _make_recommendation(strategy_name="build", track_count=2)
    generated_at = datetime(2026, 6, 14, 3, 30, 45)

    name = default_export_filename(recommendation, generated_at=generated_at, suffix="!!!")

    assert name == "20260614_033045_build_2_tracks"
    assert "__" not in name
