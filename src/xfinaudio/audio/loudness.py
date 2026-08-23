"""FFmpeg EBU R128 parsing and command construction for loudness analysis.

Process execution, capability preflight, and cancellation are intentionally deferred to
WU1b. This module defines the deterministic, shell-free boundary those operations use.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

CURRENT_LOUDNESS_VERSION = 1
MINIMUM_LOUDNESS_DURATION_SECONDS = 3.0


class LoudnessStatus(StrEnum):
    """Classify measured and typed non-measurement loudness outcomes."""

    MEASURED = "measured"
    UNMEASURABLE = "unmeasurable"
    TRANSIENT_FAILURE = "transient_failure"
    UNSUPPORTED = "unsupported"
    TOO_SHORT = "too_short"


class LoudnessProfile(BaseModel):
    """Versioned EBU R128 measurement and its post-write source identity."""

    model_config = ConfigDict(frozen=True)

    lufs_integrated: float
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


@runtime_checkable
class LoudnessAnalyzer(Protocol):
    """Deterministic FFmpeg loudness boundary before process execution is added."""

    def build_command(self, path: Path | str) -> tuple[str, ...]:
        """Return the exact FFmpeg argument vector for one audio file."""
        ...

    def parse_stderr(self, stderr: str, *, duration_seconds: float) -> LoudnessProfile:
        """Parse a pinned-build EBU R128 summary into a typed profile."""
        ...


class FfmpegLoudnessAdapter:
    """Construct and parse the pinned FFmpeg `ebur128=peak=true` contract."""

    def __init__(self, executable: Path | str, *, engine_fingerprint: str) -> None:
        self._executable = Path(executable)
        self._engine_fingerprint = engine_fingerprint

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
        loudness_range_lra = _required_summary_value(stderr, "LRA", "LU")
        true_peak_dbtp = _required_summary_value(stderr, "Peak", "dBFS")
        return LoudnessProfile(
            lufs_integrated=integrated_lufs,
            loudness_range_lra=loudness_range_lra,
            true_peak_dbtp=true_peak_dbtp,
            status=LoudnessStatus.MEASURED,
            engine_fingerprint=self._engine_fingerprint,
        )


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
    "FfmpegLoudnessAdapter",
    "LoudnessAnalyzer",
    "LoudnessParseError",
    "LoudnessProfile",
    "LoudnessStatus",
]
