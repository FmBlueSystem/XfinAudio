"""Tests for pure audio analysis planning."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.audio.analysis_planning import plan_analysis_paths
from xfinaudio.audio.spectral_profile import SpectralProfile


def test_plan_analysis_paths_returns_fresh_cache_hits(tmp_path: Path) -> None:
    audio_path = tmp_path / "track.flac"
    audio_path.write_text("audio")
    stat = audio_path.stat()
    profile = SpectralProfile(red_ratio=0.1, green_ratio=0.8, blue_ratio=0.1, dominant_color="GREEN")
    cache = {str(audio_path): (stat.st_mtime_ns, stat.st_size, profile)}

    plan = plan_analysis_paths([audio_path], cache=cache)

    assert plan.results == {str(audio_path): profile}
    assert plan.pending_paths == []


def test_plan_analysis_paths_deduplicates_uncached_pending_paths(tmp_path: Path) -> None:
    audio_path = tmp_path / "track.flac"
    audio_path.write_text("audio")

    plan = plan_analysis_paths([audio_path, audio_path], cache={})

    assert plan.results == {}
    assert plan.pending_paths == [audio_path]
