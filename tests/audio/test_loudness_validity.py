"""Loudness validity; synthetic data and in-memory writers only."""

from unittest.mock import Mock

import pytest

from xfinaudio.audio.loudness import (
    CURRENT_LOUDNESS_VERSION,
    FfmpegLoudnessAdapter,
    LoudnessParseError,
    LoudnessProfile,
    LoudnessStatus,
    is_complete_measurement,
)
from xfinaudio.audio.loudness_tags import LoudnessTagWriteStatus, recover_loudness_profile, write_loudness_tags
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.recommendation.playlist_service import _measured_lufs

SUMMARY = "  I: -20.0 LUFS\n  LRA: 20.0 LU\n  Peak: -17.0 dBFS\n"


def adapter():
    return FfmpegLoudnessAdapter("/not-executed/ffmpeg", engine_fingerprint="synthetic")


@pytest.mark.parametrize("duration", [3.0, 3.3, 20.0, 59.9])
def test_unstable_lra_is_partial_and_never_reaches_tag_loader(duration, tmp_path):
    profile = adapter().parse_stderr(SUMMARY, duration_seconds=duration)
    assert profile.status is LoudnessStatus.TOO_SHORT
    assert profile.lufs_integrated == -20
    assert profile.true_peak_dbtp == -17
    assert profile.loudness_range_lra is None
    assert not is_complete_measurement(profile)
    loader = Mock(side_effect=AssertionError("must not read or write tags"))
    assert (
        write_loudness_tags(tmp_path / "synthetic.wav", profile, load_audio=loader).status
        is LoudnessTagWriteStatus.UNSUPPORTED
    )
    loader.assert_not_called()


def test_sixty_seconds_accepts_valid_complete_measurement():
    profile = adapter().parse_stderr(SUMMARY, duration_seconds=60.0)
    assert profile.status is LoudnessStatus.MEASURED and is_complete_measurement(profile)


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "9" * 400])
def test_nonfinite_or_overflow_summary_rejected(raw):
    with pytest.raises(LoudnessParseError):
        adapter().parse_stderr(SUMMARY.replace("-20.0", raw), duration_seconds=60)


def test_below_gate_is_not_a_measured_minus70():
    p = adapter().parse_stderr(SUMMARY.replace("-20.0", "-70.0"), duration_seconds=60)
    assert p.status is LoudnessStatus.UNMEASURABLE
    assert p.lufs_integrated is None
    assert not is_complete_measurement(p)


@pytest.mark.parametrize(
    "field,value", [("lufs_integrated", float("nan")), ("true_peak_dbtp", float("inf")), ("loudness_range_lra", -1)]
)
def test_invalid_model_metrics_rejected(field, value):
    data = {
        "lufs_integrated": -20,
        "loudness_range_lra": 0,
        "true_peak_dbtp": -17,
        "status": LoudnessStatus.MEASURED,
        "engine_fingerprint": "synthetic",
    }
    data[field] = value
    with pytest.raises(ValueError):
        LoudnessProfile.model_validate(data)


def test_stale_version_cannot_write_tags_or_filter_tracks(tmp_path):
    current = adapter().parse_stderr(SUMMARY, duration_seconds=60)
    old = current.model_copy(update={"analysis_version": 1})
    assert CURRENT_LOUDNESS_VERSION > 1
    assert not is_complete_measurement(old)
    assert _measured_lufs(TrackRecord(path="synthetic", loudness_profile=old)) is None
    loader = Mock(side_effect=AssertionError("stale tags must not be loaded"))
    assert write_loudness_tags(tmp_path / "x.wav", old, load_audio=loader).status is LoudnessTagWriteStatus.UNSUPPORTED
    loader.assert_not_called()


def test_old_cache_and_tag_never_relabel_as_current(tmp_path):
    path = tmp_path / "synthetic.flac"
    path.write_bytes(b"synthetic identity only")
    stat = path.stat()
    old = (
        adapter()
        .parse_stderr(SUMMARY, duration_seconds=60)
        .model_copy(
            update={"analysis_version": 1, "source_mtime_ns": stat.st_mtime_ns, "source_size_bytes": stat.st_size}
        )
    )
    repo = TrackRepository(tmp_path / "synthetic.db")
    repo.save_scan_results([TrackRecord(path=str(path), loudness_profile=old)])
    assert repo.load_loudness_profile_cache([str(path)], engine_fingerprint="synthetic") == {}
    assert (
        recover_loudness_profile(path, {"XFINAUDIO_LOUDNESS": ["lufs=-20;lra=20;dbtp=-17;v=1;engine=synthetic"]})
        is None
    )


@pytest.mark.parametrize("duration", [float("nan"), float("inf"), -1])
def test_invalid_duration_never_yields_complete_measurement(duration):
    p = adapter().parse_stderr(SUMMARY, duration_seconds=duration)
    assert not is_complete_measurement(p)
