#!/usr/bin/env python3
"""Inspect audio metadata tags without modifying audio files.

The script is intentionally read-only: it uses mutagen.File(...), never calls save(),
and redacts long binary/base64-like payloads so reports and fixtures stay small.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mutagen._file import File

MAX_VALUE_LENGTH = 160
BINARY_MARKER = "<binary data redacted>"


def inspect_paths(paths: list[Path]) -> list[dict[str, Any]]:
    """Return safe metadata summaries for paths using read-only mutagen access."""
    summaries = []
    for path in paths:
        audio = File(path, easy=False)
        tags = _safe_tags(audio.tags.items()) if audio is not None and audio.tags is not None else {}
        summaries.append(
            {
                "file_name": path.name,
                "file_type": type(audio).__name__ if audio is not None else None,
                "exists": path.exists(),
                "tag_count": len(tags),
                "tags": tags,
            }
        )
    return summaries


def _safe_tags(items: Any) -> dict[str, list[str]]:
    return {str(key): [_safe_value(value)] for key, value in sorted(items, key=lambda item: str(item[0]).casefold())}


def _safe_value(value: Any) -> str:
    text = repr(value)
    if "data=b'" in text or 'data=b"' in text:
        return BINARY_MARKER
    if len(text) > MAX_VALUE_LENGTH:
        return f"{text[:MAX_VALUE_LENGTH]}... <truncated>"
    return text


def main() -> None:
    """Run the tag inspector CLI."""
    parser = argparse.ArgumentParser(description="Inspect audio tags without mutating files.")
    parser.add_argument("paths", nargs="+", type=Path, help="Audio files to inspect")
    parser.add_argument("--output", "-o", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    summaries = inspect_paths(args.paths)
    output = json.dumps(summaries, ensure_ascii=False, indent=2)
    if args.output is None:
        print(output)
    else:
        args.output.write_text(f"{output}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
