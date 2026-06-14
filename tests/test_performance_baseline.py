"""Performance baseline tests for core audio-free workflows."""

from __future__ import annotations

import time

import pytest

from tests.fixtures.performance_tracks import make_complete_tracks
from xfinaudio.exporting.playlist_exporters import default_exporter_registry, export_quality_report_json
from xfinaudio.quality.dj_readiness import build_dj_readiness_report
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import recommend_playlist

# Thresholds are generous to avoid CI flakiness; they protect against severe regressions.
_RECOMMEND_THRESHOLDS = {50: 2.0, 100: 4.0}
_EXPORT_THRESHOLD = 1.0
_QUALITY_THRESHOLD = 1.0
_READINESS_THRESHOLD = 1.0


@pytest.mark.parametrize("track_count", [50, 100])
def test_recommend_playlist_performance(track_count: int) -> None:
    """Recommendation should complete within the baseline threshold."""
    tracks = make_complete_tracks(track_count)

    start = time.perf_counter()
    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey")
    elapsed = time.perf_counter() - start

    assert len(recommendation.ordered_tracks) > 0
    assert elapsed < _RECOMMEND_THRESHOLDS[track_count]


def test_export_playlist_performance() -> None:
    """In-memory export of a 100-track recommendation should be fast."""
    tracks = make_complete_tracks(100)
    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey")
    registry = default_exporter_registry()

    start = time.perf_counter()
    for fmt in ("json", "csv", "m3u"):
        registry.export(fmt, recommendation)
    elapsed = time.perf_counter() - start

    assert elapsed < _EXPORT_THRESHOLD


def test_quality_report_performance() -> None:
    """Quality report generation for a 100-track recommendation should be fast."""
    tracks = make_complete_tracks(100)
    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey")
    quality_report = build_quality_report(recommendation)

    start = time.perf_counter()
    json_output = export_quality_report_json(quality_report)
    elapsed = time.perf_counter() - start

    assert json_output
    assert elapsed < _QUALITY_THRESHOLD


def test_dj_readiness_report_performance() -> None:
    """DJ readiness report generation for a 100-track recommendation should be fast."""
    tracks = make_complete_tracks(100)
    recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey")
    quality_report = build_quality_report(recommendation)

    start = time.perf_counter()
    build_dj_readiness_report(recommendation, quality_report)
    elapsed = time.perf_counter() - start

    assert elapsed < _READINESS_THRESHOLD
