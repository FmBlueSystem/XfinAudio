"""Tests for the FFmpeg EBU R128 loudness boundary."""

from __future__ import annotations

import base64
import math
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from shutil import copyfile
from typing import Any

import numpy as np
import pyloudnorm as pyln
import pytest
from mutagen.id3 import APIC
from mutagen.wave import WAVE

from xfinaudio.audio.loudness import (
    MINIMUM_LOUDNESS_DURATION_SECONDS,
    FfmpegCapabilityError,
    FfmpegLoudnessAdapter,
    FfmpegProbeResult,
    LoudnessAnalyzer,
    LoudnessParseError,
    LoudnessProfile,
    LoudnessStatus,
)
from xfinaudio.audio.loudness_runtime import resolve_ffmpeg

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


def test_adapter_analyzes_embedded_cover_art_without_selecting_it_as_audio(tmp_path: Path) -> None:
    audio_file = tmp_path / "cover-art.wav"
    copyfile(FIXTURES / "synthetic_tone_1khz.wav", audio_file)
    audio = WAVE(audio_file)
    audio.add_tags()
    audio.tags.add(
        APIC(
            encoding=3,
            mime="image/png",
            type=3,
            desc="cover",
            data=base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlWZQAAAABJRU5ErkJggg=="
            ),
        )
    )
    audio.save()
    tagged_audio = WAVE(audio_file)
    assert tagged_audio.tags is not None
    assert tagged_audio.tags["APIC:cover"].mime == "image/png"

    executable = tmp_path / "ffmpeg"
    golden_stderr = (FIXTURES / "synthetic_tone_1khz_ebu.stderr").read_text()
    executable.write_text(
        f"""#!{sys.executable}
import sys
from mutagen.wave import WAVE

args = sys.argv[1:]
audio_path = args[args.index("-i") + 1]
audio = WAVE(audio_path)
assert "APIC:cover" in audio.tags and audio.info.length >= 3
assert args[args.index("-map") + 1] == "0:a:0" and "-vn" in args
sys.stderr.write({golden_stderr!r})
""",
        encoding="utf-8",
    )
    executable.chmod(0o755)

    profile = FfmpegLoudnessAdapter(executable, engine_fingerprint="cover-art-fixture").analyze(
        audio_file, duration_seconds=3.0
    )

    assert profile.status is LoudnessStatus.MEASURED
    assert (profile.lufs_integrated, profile.loudness_range_lra, profile.true_peak_dbtp) == (-20.0, 20.0, -17.0)


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


class _FakeProcess:
    def __init__(self, stderr: str, *, timeout: bool = False, on_communicate: Any = None) -> None:
        self.stderr = stderr
        self.timeout = timeout
        self.on_communicate = on_communicate
        self.pid = 4242
        self.returncode: int | None = None
        self.timeouts: list[float | None] = []

    def communicate(self, *, timeout: float | None = None) -> tuple[str, str]:
        self.timeouts.append(timeout)
        if self.on_communicate is not None:
            self.on_communicate()
        if self.timeout and len(self.timeouts) == 1:
            raise subprocess.TimeoutExpired("ffmpeg", timeout or 0.0)
        return "", self.stderr


def test_preflight_requires_bundled_binary_ebur128_filter_and_true_peak(tmp_path: Path) -> None:
    executable = tmp_path / "bundle" / "ffmpeg"
    executable.parent.mkdir()
    executable.touch(mode=0o755)
    probes: list[tuple[str, ...]] = []

    def probe(command: tuple[str, ...]) -> FfmpegProbeResult:
        probes.append(command)
        output = " T.. ebur128 A->N EBU R128" if command[-1] == "-filters" else "  peak <int>\n     true 2"
        return FfmpegProbeResult(returncode=0, output=output)

    adapter = FfmpegLoudnessAdapter(executable, engine_fingerprint="ffmpeg-8.0.1-ebur128")

    adapter.preflight(probe=probe)

    assert probes == [
        (str(executable), "-hide_banner", "-filters"),
        (str(executable), "-hide_banner", "-h", "filter=ebur128"),
    ]


def test_preflight_rejects_missing_filter_or_true_peak_capability(tmp_path: Path) -> None:
    executable = tmp_path / "bundle" / "ffmpeg"
    executable.parent.mkdir()
    executable.touch(mode=0o755)
    adapter = FfmpegLoudnessAdapter(executable, engine_fingerprint="ffmpeg-8.0.1-ebur128")

    with pytest.raises(FfmpegCapabilityError, match="ebur128"):
        adapter.preflight(probe=lambda _command: FfmpegProbeResult(returncode=0, output=""))

    def no_true_peak(command: tuple[str, ...]) -> FfmpegProbeResult:
        output = " T.. ebur128 A->N EBU R128" if command[-1] == "-filters" else "  peak <int>\n     sample 1"
        return FfmpegProbeResult(returncode=0, output=output)

    with pytest.raises(FfmpegCapabilityError, match="true peak"):
        adapter.preflight(probe=no_true_peak)


def test_analyze_uses_injected_shell_free_process_with_devnull_and_parses_output(tmp_path: Path) -> None:
    executable = tmp_path / "bundle" / "ffmpeg"
    audio_file = tmp_path / "cover-art.flac"
    process = _FakeProcess((FIXTURES / "synthetic_tone_1khz_ebu.stderr").read_text())
    launches: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    def process_factory(command: tuple[str, ...], **kwargs: Any) -> _FakeProcess:
        launches.append((command, kwargs))
        return process

    adapter = FfmpegLoudnessAdapter(
        executable,
        engine_fingerprint="ffmpeg-8.0.1-ebur128",
        process_factory=process_factory,
        timeout_seconds=9.5,
    )

    profile = adapter.analyze(audio_file, duration_seconds=3.0)

    assert profile.status is LoudnessStatus.MEASURED
    assert process.timeouts == [9.5]
    assert launches == [
        (
            adapter.build_command(audio_file),
            {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.PIPE,
                "text": True,
                "shell": False,
                "start_new_session": True,
            },
        )
    ]


def test_timeout_and_shutdown_kill_the_live_process_group_and_return_transient_failure(tmp_path: Path) -> None:
    executable = tmp_path / "bundle" / "ffmpeg"
    audio_file = tmp_path / "timed-out.flac"
    killed: list[int] = []
    process = _FakeProcess("", timeout=True)

    def process_factory(_command: tuple[str, ...], **_kwargs: Any) -> _FakeProcess:
        return process

    adapter = FfmpegLoudnessAdapter(
        executable,
        engine_fingerprint="ffmpeg-8.0.1-ebur128",
        process_factory=process_factory,
        kill_process_group=lambda pid: killed.append(pid),
    )

    profile = adapter.analyze(audio_file, duration_seconds=3.0)

    assert profile.status is LoudnessStatus.TRANSIENT_FAILURE
    assert profile.lufs_integrated is None
    assert killed == [process.pid]


def test_preflight_requires_an_executable_and_successful_structured_probes(tmp_path: Path) -> None:
    executable = tmp_path / "bundle" / "ffmpeg"
    executable.parent.mkdir()
    executable.touch(mode=0o755)
    adapter = FfmpegLoudnessAdapter(executable, engine_fingerprint="ffmpeg-8.0.1-ebur128")

    def valid_probe(command: tuple[str, ...]) -> FfmpegProbeResult:
        if command[-1] == "-filters":
            return FfmpegProbeResult(0, " T.. ebur128 A->N EBU R128")
        return FfmpegProbeResult(0, "  peak <int> set peak mode\n     none 0\n     true 2")

    adapter.preflight(probe=valid_probe)

    executable.chmod(0o644)
    with pytest.raises(FfmpegCapabilityError, match="executable"):
        adapter.preflight(probe=valid_probe)

    executable.chmod(0o755)
    with pytest.raises(FfmpegCapabilityError, match="probe"):
        adapter.preflight(probe=lambda _command: FfmpegProbeResult(1, " T.. ebur128 A->N EBU R128"))


def test_preflight_rejects_unrelated_peak_and_true_words(tmp_path: Path) -> None:
    executable = tmp_path / "bundle" / "ffmpeg"
    executable.parent.mkdir()
    executable.touch(mode=0o755)
    adapter = FfmpegLoudnessAdapter(executable, engine_fingerprint="ffmpeg-8.0.1-ebur128")

    def misleading_probe(command: tuple[str, ...]) -> FfmpegProbeResult:
        if command[-1] == "-filters":
            return FfmpegProbeResult(0, " T.. ebur128 A->N EBU R128")
        return FfmpegProbeResult(0, "peak detection is true for another filter")

    with pytest.raises(FfmpegCapabilityError, match="true peak"):
        adapter.preflight(probe=misleading_probe)


class _TimeoutReapingProcess:
    pid = 5252
    returncode: int | None = None

    def __init__(self) -> None:
        self.communicate_timeouts: list[float | None] = []
        self.reaped = False

    def communicate(self, *, timeout: float | None = None) -> tuple[str, str]:
        self.communicate_timeouts.append(timeout)
        if len(self.communicate_timeouts) == 1:
            raise subprocess.TimeoutExpired("ffmpeg", timeout or 0.0)
        self.reaped = True
        return "", ""


def test_timeout_kills_the_group_then_reaps_the_owner_process(tmp_path: Path) -> None:
    process = _TimeoutReapingProcess()
    killed: list[int] = []
    adapter = FfmpegLoudnessAdapter(
        tmp_path / "bundle" / "ffmpeg",
        engine_fingerprint="ffmpeg-8.0.1-ebur128",
        process_factory=lambda _command, **_kwargs: process,
        kill_process_group=killed.append,
    )

    profile = adapter.analyze(tmp_path / "timed-out.flac", duration_seconds=3.0)

    assert profile.status is LoudnessStatus.TRANSIENT_FAILURE
    assert killed == [process.pid]
    assert process.communicate_timeouts == [120.0, None]
    assert process.reaped is True


class _RaceProcess:
    pid = 6262
    returncode: int | None = None

    def __init__(self, fixture_stderr: str) -> None:
        self._fixture_stderr = fixture_stderr
        self.killed = threading.Event()
        self.reaped = threading.Event()

    def communicate(self, *, timeout: float | None = None) -> tuple[str, str]:
        del timeout
        assert self.killed.wait(timeout=1.0)
        self.reaped.set()
        return "", self._fixture_stderr


@pytest.mark.parametrize("action_name", ["cancel", "shutdown"])
def test_cancel_and_shutdown_cover_spawn_registration_race_and_wait_for_reaping(
    tmp_path: Path, action_name: str
) -> None:
    factory_entered = threading.Event()
    release_factory = threading.Event()
    action_done = threading.Event()
    process = _RaceProcess((FIXTURES / "synthetic_tone_1khz_ebu.stderr").read_text())
    killed: list[int] = []

    def process_factory(_command: tuple[str, ...], **_kwargs: Any) -> _RaceProcess:
        factory_entered.set()
        assert release_factory.wait(timeout=1.0)
        return process

    def kill_process_group(pid: int) -> None:
        killed.append(pid)
        process.killed.set()

    adapter = FfmpegLoudnessAdapter(
        tmp_path / "bundle" / "ffmpeg",
        engine_fingerprint="ffmpeg-8.0.1-ebur128",
        process_factory=process_factory,
        kill_process_group=kill_process_group,
    )
    analysis = threading.Thread(target=lambda: adapter.analyze(tmp_path / "race.flac", duration_seconds=3.0))
    action = threading.Thread(target=lambda: (getattr(adapter, action_name)(), action_done.set()))
    analysis.start()
    assert factory_entered.wait(timeout=1.0)
    action.start()
    try:
        assert action_done.wait(timeout=0.1) is False
    finally:
        release_factory.set()
    analysis.join(timeout=1.0)
    action.join(timeout=1.0)

    assert analysis.is_alive() is False
    assert action.is_alive() is False
    assert killed == [process.pid]
    assert process.reaped.is_set()
    if action_name == "cancel":
        assert adapter.analyze(tmp_path / "restart.flac", duration_seconds=3.0).status is LoudnessStatus.MEASURED


@pytest.mark.parametrize("fixture_name", ["synthetic_tone_1khz_aac.m4a", "synthetic_tone_1khz_alac.m4a"])
def test_frozen_resolved_ffmpeg_measures_real_synthetic_m4a(fixture_name: str, tmp_path: Path) -> None:
    executable = Path(os.environ.get("XFINAUDIO_FFMPEG_BINARY") or shutil.which("ffmpeg") or "")
    if not executable.is_file():
        pytest.skip("requires XFINAUDIO_FFMPEG_BINARY or a developer FFmpeg")
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "ffmpeg").symlink_to(executable)
    frozen_ffmpeg = resolve_ffmpeg(frozen=True, bundle_dir=bundle_dir)
    assert frozen_ffmpeg == executable.resolve()
    assert frozen_ffmpeg is not None

    profile = FfmpegLoudnessAdapter(frozen_ffmpeg, engine_fingerprint="fixture-real-m4a").analyze(
        FIXTURES / fixture_name, duration_seconds=3.0
    )

    assert profile.status is LoudnessStatus.MEASURED
    lufs = profile.lufs_integrated
    lra = profile.loudness_range_lra
    true_peak = profile.true_peak_dbtp
    assert lufs is not None and lra is not None and true_peak is not None
    assert all(math.isfinite(value) for value in (lufs, lra, true_peak))
    assert -80.0 < lufs < 0.0
    assert 0.0 <= lra < 80.0
    assert -80.0 < true_peak <= 10.0
