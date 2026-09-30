"""Text escaping for spreadsheet-facing CSV; JSON retains the original values."""

from __future__ import annotations

import unicodedata


def spreadsheet_safe_text(value: str) -> str:
    """Prefix formula-like text with an apostrophe, preserving the original text.

    Ignore leading Unicode whitespace/control/format characters when detecting
    a formula. Consumers should import CSV text columns as text; use JSON when
    the exact unescaped metadata is needed. Do not use this for numeric columns.
    """
    for char in value:
        if char.isspace() or unicodedata.category(char) in {"Cc", "Cf"}:
            continue
        return "'" + value if char in "=+-@" else value
    return value
