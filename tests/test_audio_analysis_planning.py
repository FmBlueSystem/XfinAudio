"""Tests for pure audio analysis planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from xfinaudio.audio.analysis_planning import plan_analysis_paths
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile


@pytest.mark.parametrize(
    ("version", "is_hit"),
    [(1, False), (CURRENT_ANALYSIS_VERSION, True), (CURRENT_ANALYSIS_VERSION + 1, False)],
)
def test_plan_analysis_paths_requires_exact_current_cache_version(tmp_path: Path, version: int, is_hit: bool) -> None:
    audio_path = tmp_path / "track.flac"
    audio_path.write_text("audio")
    stat = audio_path.stat()
    profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        dominant_color="GREEN",
        analysis_version=version,
    )
    cache = {str(audio_path): (stat.st_mtime_ns, stat.st_size, profile)}

    plan = plan_analysis_paths([audio_path], cache=cache)

    assert plan.results == ({str(audio_path): profile} if is_hit else {})
    assert plan.pending_paths == ([] if is_hit else [audio_path])


def test_plan_analysis_paths_deduplicates_uncached_pending_paths(tmp_path: Path) -> None:
    audio_path = tmp_path / "track.flac"
    audio_path.write_text("audio")

    plan = plan_analysis_paths([audio_path, audio_path], cache={})

    assert plan.results == {}
    assert plan.pending_paths == [audio_path]
