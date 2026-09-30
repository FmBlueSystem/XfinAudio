"""Shared validity contract for metadata-derived tempo values."""

from math import isfinite


def is_valid_bpm(value: float | None) -> bool:
    """Accept finite positive BPM without imposing a musical genre/range limit."""
    return value is not None and isfinite(value) and value > 0
