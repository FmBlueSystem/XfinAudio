"""Immutable loudness target policy shared by strategy filtering and future settings."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LOUDNESS_TARGET_LUFS = -10.0
DEFAULT_LOUDNESS_TOLERANCE_LU = 2.0


@dataclass(frozen=True)
class LoudnessBand:
    """Absolute integrated-loudness target and inclusive tolerance for one pool."""

    target_lufs: float = DEFAULT_LOUDNESS_TARGET_LUFS
    tolerance_lu: float = DEFAULT_LOUDNESS_TOLERANCE_LU

    def contains(self, lufs: float) -> bool:
        return abs(lufs - self.target_lufs) <= self.tolerance_lu


DEFAULT_LOUDNESS_BAND = LoudnessBand()

__all__ = [
    "DEFAULT_LOUDNESS_BAND",
    "DEFAULT_LOUDNESS_TARGET_LUFS",
    "DEFAULT_LOUDNESS_TOLERANCE_LU",
    "LoudnessBand",
]
