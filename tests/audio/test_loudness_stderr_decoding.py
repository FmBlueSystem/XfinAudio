"""Real subprocess bytes, synthetic paths and in-memory tag writer only."""

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from xfinaudio.audio.loudness import FfmpegLoudnessAdapter, LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_completion import LoudnessCompletionService
from xfinaudio.audio.loudness_tags import LoudnessTagWriteResult, LoudnessTagWriteStatus
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository

SUMMARY = b"  I: -11.5 LUFS\n  LRA: 2.3 LU\n  Peak: -1.5 dBFS\n"
INVALID_METADATA = b"Metadata:\n  title: synthetic\xff\xfe\x80\xe2(\xa1\n"


def _adapter(payload: bytes, *, returncode: int = 0, launches: list | None = None):
    def launch(command: tuple[str, ...], **kwargs: Any) -> Any:
        if launches is not None:
            launches.append(command)
        # The actual Popen text decoder sees these bytes; no audio file is opened.
        script = f"import os,sys; os.write(2, {payload!r}); sys.exit({returncode})"
        return subprocess.Popen([sys.executable, "-c", script], **kwargs)

    return FfmpegLoudnessAdapter("/not-executed/ffmpeg", engine_fingerprint="synthetic", process_factory=launch)


@pytest.mark.parametrize("metadata", [b"ASCII metadata\n", "Title: sintético\n".encode(), INVALID_METADATA])
def test_valid_summary_survives_metadata_encoding(metadata):
    profile = _adapter(metadata + SUMMARY).analyze("/not-opened/synthetic.wav", duration_seconds=120)
    assert profile.status is LoudnessStatus.MEASURED
    assert (profile.lufs_integrated, profile.loudness_range_lra, profile.true_peak_dbtp) == (-11.5, 2.3, -1.5)


@pytest.mark.parametrize(
    "summary", [b"", SUMMARY.replace(b"-11.5", b"-1\xff1.5"), SUMMARY.replace(b"LUFS", b"LU\xffFS")]
)
def test_corrupt_or_missing_summary_is_not_repaired_by_decoding(summary):
    profile = _adapter(INVALID_METADATA + summary).analyze("/not-opened/synthetic.wav", duration_seconds=120)
    assert profile.status is LoudnessStatus.UNMEASURABLE
    assert profile.lufs_integrated is None


def test_nonzero_exit_with_valid_summary_stays_unmeasurable():
    profile = _adapter(INVALID_METADATA + SUMMARY, returncode=1).analyze("/not-opened/x.wav", duration_seconds=120)
    assert profile.status is LoudnessStatus.UNMEASURABLE


def test_force_retry_replaces_cached_failure_without_reading_or_writing_audio(tmp_path: Path):
    path = tmp_path / "synthetic.wav"
    path.write_bytes(b"file identity only; not audio")
    before = path.read_bytes()
    stat = path.stat()
    failed = LoudnessProfile(
        lufs_integrated=None,
        loudness_range_lra=None,
        true_peak_dbtp=None,
        status=LoudnessStatus.TRANSIENT_FAILURE,
        engine_fingerprint="synthetic",
        source_mtime_ns=stat.st_mtime_ns,
        source_size_bytes=stat.st_size,
    )
    record = TrackRecord(path=str(path), duration=120, loudness_profile=failed)
    repository = TrackRepository(tmp_path / "synthetic.sqlite3")
    repository.save_scan_results([record])
    launches: list = []
    service = LoudnessCompletionService(
        _adapter(INVALID_METADATA + SUMMARY, launches=launches),
        engine_fingerprint="synthetic",
        tag_writer=lambda _path, _profile: LoudnessTagWriteResult(status=LoudnessTagWriteStatus.UNSUPPORTED),
    )
    assert service.complete([record], repository)[str(path)].status is LoudnessStatus.TRANSIENT_FAILURE
    assert not launches
    result = service.complete([record], repository, force_reanalyze=True)[str(path)]
    assert result.status is LoudnessStatus.MEASURED
    assert result.lufs_integrated == -11.5
    assert len(launches) == 1
    assert repository.load_loudness_profile_cache([str(path)], engine_fingerprint="synthetic")[str(path)] == result
    assert path.read_bytes() == before
