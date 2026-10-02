"""Shared display-only metadata formatting; never changes source values."""


def format_bpm(bpm: float | None, *, missing: str = "—") -> str:
    """Preserve tempo precision while omitting an unnecessary decimal zero."""
    if bpm is None or bpm == 0:
        return missing
    return str(bpm).removesuffix(".0")
