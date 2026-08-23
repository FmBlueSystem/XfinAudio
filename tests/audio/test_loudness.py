"""Tests for the FFmpeg EBU R128 loudness boundary."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import pytest

from xfinaudio.audio.loudness import (
    MINIMUM_LOUDNESS_DURATION_SECONDS,
    FfmpegLoudnessAdapter,
    LoudnessAnalyzer,
    LoudnessParseError,
    LoudnessProfile,
    LoudnessStatus,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "loudness"


def test_profile_carries_versioned_post_write_identity() -> None:
    profile = LoudnessProfile(
        lufs_integrated=-10.4,
        loudness_range_lra=4.8,
        true_peak_dbtp=-0.3,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint="ffmpeg-8.0.1-ebur128",
        source_mtime_ns=123,
        source_size_bytes=456,
        source_audio_md5="0123456789abcdef0123456789abcdef",
    )

    assert profile.analysis_version == 1
    assert profile.source_mtime_ns == 123
    assert profile.source_size_bytes == 456


def test_adapter_builds_the_exact_shell_free_ffmpeg_command(tmp_path: Path) -> None:
    executable = tmp_path / "ffmpeg"
    audio_file = tmp_path / "cover-art.flac"
    adapter = FfmpegLoudnessAdapter(executable, engine_fingerprint="ffmpeg-8.0.1-ebur128")

    assert isinstance(adapter, LoudnessAnalyzer)
    assert adapter.build_command(audio_file) == (
        str(executable),
        "-nostdin",
        "-hide_banner",
        "-i",
        str(audio_file),
        "-map",
        "0:a:0",
        "-vn",
        "-af",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    )


def test_adapter_parses_the_pinned_synthetic_golden_output_with_lufs_sanity() -> None:
    adapter = FfmpegLoudnessAdapter("/bundle/ffmpeg", engine_fingerprint="ffmpeg-8.0.1-ebur128")
    stderr = (FIXTURES / "synthetic_tone_1khz_ebu.stderr").read_text()

    profile = adapter.parse_stderr(stderr, duration_seconds=3.0)

    assert profile.status is LoudnessStatus.MEASURED
    assert profile.lufs_integrated == pytest.approx(-20.0, abs=0.1)
    assert profile.loudness_range_lra == pytest.approx(20.0)
    assert profile.true_peak_dbtp == pytest.approx(-17.0)
    samples = 0.142 * np.sin(2 * np.pi * 1_000 * np.arange(48_000 * 3) / 48_000)
    oracle_lufs = pyln.Meter(48_000).integrated_loudness(samples)
    assert profile.lufs_integrated == pytest.approx(oracle_lufs, abs=0.1)


def test_adapter_rejects_malformed_pinned_output() -> None:
    adapter = FfmpegLoudnessAdapter("/bundle/ffmpeg", engine_fingerprint="ffmpeg-8.0.1-ebur128")

    with pytest.raises(LoudnessParseError):
        adapter.parse_stderr("Integrated loudness:\n  I: -20.0 LUFS\n", duration_seconds=10.0)


def test_short_material_keeps_integrated_lufs_but_omits_lra_and_true_peak() -> None:
    adapter = FfmpegLoudnessAdapter("/bundle/ffmpeg", engine_fingerprint="ffmpeg-8.0.1-ebur128")
    stderr = (FIXTURES / "synthetic_short_ebu.stderr").read_text()

    profile = adapter.parse_stderr(stderr, duration_seconds=MINIMUM_LOUDNESS_DURATION_SECONDS - 0.01)

    assert profile.status is LoudnessStatus.TOO_SHORT
    assert profile.lufs_integrated == pytest.approx(-20.0)
    assert profile.loudness_range_lra is None
    assert profile.true_peak_dbtp is None
