"""FFmpeg EBU R128 preflight, execution, and parsing for loudness analysis."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

CURRENT_LOUDNESS_VERSION = 1
MINIMUM_LOUDNESS_DURATION_SECONDS = 3.0


class LoudnessStatus(StrEnum):
    """Persisted outcome of one loudness analysis attempt."""

    MEASURED = "measured"
    UNMEASURABLE = "unmeasurable"
    TRANSIENT_FAILURE = "transient_failure"
    UNSUPPORTED = "unsupported"
    TOO_SHORT = "too_short"


class LoudnessProfile(BaseModel):
    """Versioned EBU R128 measurement and its post-write source identity."""

    model_config = ConfigDict(frozen=True)

    lufs_integrated: float | None
    loudness_range_lra: float | None
    true_peak_dbtp: float | None
    status: LoudnessStatus
    analysis_version: int = Field(default=CURRENT_LOUDNESS_VERSION, ge=1)
    engine_fingerprint: str = Field(min_length=1)
    source_mtime_ns: int | None = Field(default=None, ge=0)
    source_size_bytes: int | None = Field(default=None, ge=0)
    source_audio_md5: str | None = None


class LoudnessParseError(ValueError):
    """Raised when the pinned FFmpeg EBU R128 summary is incomplete or malformed."""


class FfmpegCapabilityError(RuntimeError):
    """Raised when bundled FFmpeg cannot provide the required EBU R128 contract."""


@dataclass(frozen=True)
class FfmpegProbeResult:
    """Output of a preflight probe, including the command exit status."""

    returncode: int
    output: str


class _RunningProcess(Protocol):
    returncode: int | None

    def communicate(self, *, timeout: float | None = None) -> tuple[str, str]:
        """Return process output or raise `TimeoutExpired`."""
        ...


ProcessFactory = Callable[..., _RunningProcess]
CapabilityProbe = Callable[[tuple[str, ...]], FfmpegProbeResult]


@runtime_checkable
class LoudnessAnalyzer(Protocol):
    """Pinned FFmpeg loudness boundary including process execution."""

    def build_command(self, path: Path | str) -> tuple[str, ...]:
        """Return the exact FFmpeg argument vector for one audio file."""
        ...

    def preflight(self, *, probe: CapabilityProbe | None = None) -> None:
        """Fail closed unless the pinned executable supports true-peak EBU R128."""
        ...

    def analyze(self, path: Path | str, *, duration_seconds: float) -> LoudnessProfile:
        """Run one analysis and return a typed profile or typed failure."""
        ...

    def parse_stderr(self, stderr: str, *, duration_seconds: float) -> LoudnessProfile:
        """Parse a pinned-build EBU R128 summary into a typed profile."""
        ...


class FfmpegLoudnessAdapter:
    """Run the pinned FFmpeg `ebur128=peak=true` contract without a shell."""

    def __init__(
        self,
        executable: Path | str,
        *,
        engine_fingerprint: str,
        process_factory: ProcessFactory = subprocess.Popen,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._executable = Path(executable)
        self._engine_fingerprint = engine_fingerprint
        self._process_factory = process_factory
        self._timeout_seconds = timeout_seconds

    def build_command(self, path: Path | str) -> tuple[str, ...]:
        """Build a shell-free command that always selects the first audio stream."""
        return (
            str(self._executable),
            "-nostdin",
            "-hide_banner",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-vn",
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        )

    def preflight(self, *, probe: CapabilityProbe | None = None) -> None:
        """Fail closed unless this executable exposes the required FFmpeg features."""
        executable_is_valid = (
            self._executable.is_absolute() and self._executable.is_file() and os.access(self._executable, os.X_OK)
        )
        if not executable_is_valid:
            raise FfmpegCapabilityError("Bundled FFmpeg executable must exist at an executable absolute path")
        active_probe = probe or _default_capability_probe
        filters = _require_successful_probe(active_probe((str(self._executable), "-hide_banner", "-filters")))
        if not _has_ebur128_filter(filters):
            raise FfmpegCapabilityError("Bundled FFmpeg does not provide the ebur128 filter")
        filter_help = _require_successful_probe(
            active_probe((str(self._executable), "-hide_banner", "-h", "filter=ebur128"))
        )
        if not _supports_true_peak(filter_help):
            raise FfmpegCapabilityError("Bundled FFmpeg ebur128 filter does not support true peak")

    def analyze(self, path: Path | str, *, duration_seconds: float) -> LoudnessProfile:
        """Execute one shell-free FFmpeg process and classify timeout failures."""
        process = self._process_factory(
            self.build_command(path),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            start_new_session=True,
        )
        try:
            _stdout, stderr = process.communicate(timeout=self._timeout_seconds)
        except subprocess.TimeoutExpired:
            return self._failure(LoudnessStatus.TRANSIENT_FAILURE)
        if process.returncode not in (None, 0):
            return self._failure(LoudnessStatus.UNMEASURABLE)
        try:
            return self.parse_stderr(stderr, duration_seconds=duration_seconds)
        except LoudnessParseError:
            return self._failure(LoudnessStatus.UNMEASURABLE)

    def _failure(self, status: LoudnessStatus) -> LoudnessProfile:
        return LoudnessProfile(
            lufs_integrated=None,
            loudness_range_lra=None,
            true_peak_dbtp=None,
            status=status,
            engine_fingerprint=self._engine_fingerprint,
        )

    def parse_stderr(self, stderr: str, *, duration_seconds: float) -> LoudnessProfile:
        """Parse all three required summary values, rejecting incomplete output."""
        integrated_lufs = _required_summary_value(stderr, "I", "LUFS")
        if duration_seconds < MINIMUM_LOUDNESS_DURATION_SECONDS:
            return LoudnessProfile(
                lufs_integrated=integrated_lufs,
                loudness_range_lra=None,
                true_peak_dbtp=None,
                status=LoudnessStatus.TOO_SHORT,
                engine_fingerprint=self._engine_fingerprint,
            )
        return LoudnessProfile(
            lufs_integrated=integrated_lufs,
            loudness_range_lra=_required_summary_value(stderr, "LRA", "LU"),
            true_peak_dbtp=_required_summary_value(stderr, "Peak", "dBFS"),
            status=LoudnessStatus.MEASURED,
            engine_fingerprint=self._engine_fingerprint,
        )


def _default_capability_probe(command: tuple[str, ...]) -> FfmpegProbeResult:
    result = subprocess.run(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    return FfmpegProbeResult(returncode=result.returncode, output=result.stdout or "")


def _require_successful_probe(result: FfmpegProbeResult) -> str:
    if result.returncode != 0:
        raise FfmpegCapabilityError("Bundled FFmpeg capability probe failed")
    return result.output


def _has_ebur128_filter(output: str) -> bool:
    return any(re.match(r"^\s*[.A-Z]{3}\s+ebur128\s+\S+", line) for line in output.splitlines())


def _supports_true_peak(output: str) -> bool:
    lines = output.splitlines()
    peak_option = next((index for index, line in enumerate(lines) if re.match(r"^\s{2,}peak\s+<[^>]+>", line)), None)
    if peak_option is None:
        return False
    for line in lines[peak_option + 1 :]:
        if re.match(r"^\s{2,}\w+\s+<[^>]+>", line):
            break
        if re.match(r"^\s{5,}true\s+\d+\b", line):
            return True
    return False


def _required_summary_value(stderr: str, label: str, unit: str) -> float:
    """Return one exact value from the pinned summary or fail closed."""
    pattern = re.compile(rf"^\s*{re.escape(label)}:\s*(-?\d+(?:\.\d+)?)\s+{re.escape(unit)}\s*$", re.MULTILINE)
    matches = pattern.findall(stderr)
    if len(matches) != 1:
        raise LoudnessParseError(f"Expected one {label} summary value, found {len(matches)}")
    return float(matches[0])


__all__ = [
    "CURRENT_LOUDNESS_VERSION",
    "MINIMUM_LOUDNESS_DURATION_SECONDS",
    "FfmpegCapabilityError",
    "FfmpegLoudnessAdapter",
    "FfmpegProbeResult",
    "LoudnessAnalyzer",
    "LoudnessParseError",
    "LoudnessProfile",
    "LoudnessStatus",
]
