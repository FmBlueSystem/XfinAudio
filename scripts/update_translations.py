#!/usr/bin/env python3
"""Regenerate .ts files and compile .qm files for XfinAudio i18n.

Usage:
    uv run python scripts/update_translations.py

Requires pyside6-lupdate and pyside6-lrelease (or lupdate/lrelease).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_SRC = REPO_ROOT / "src" / "xfinaudio" / "desktop"
TRANSLATIONS_DIR = REPO_ROOT / "translations"
ASSETS_TRANSLATIONS_DIR = REPO_ROOT / "assets" / "translations"

LANGUAGES = ["en", "es"]


def find_source_files() -> list[Path]:
    """Collect all Python files under the desktop package."""
    files: list[Path] = []
    for py_file in sorted(DESKTOP_SRC.rglob("*.py")):
        if py_file.name.startswith("test_"):
            continue
        files.append(py_file)
    return files


def lupdate_cmd() -> list[str]:
    """Return the lupdate command, preferring pyside6-lupdate."""
    for cmd in ("pyside6-lupdate", "lupdate"):
        result = subprocess.run(
            [cmd, "-version"],
            capture_output=True,
        )
        if result.returncode == 0:
            return [cmd]
    print("ERROR: pyside6-lupdate or lupdate not found.", file=sys.stderr)
    sys.exit(1)


def lrelease_cmd() -> list[str]:
    """Return the lrelease command, preferring pyside6-lrelease."""
    for cmd in ("pyside6-lrelease", "lrelease"):
        result = subprocess.run(
            [cmd, "-version"],
            capture_output=True,
        )
        if result.returncode == 0:
            return [cmd]
    print("ERROR: pyside6-lrelease or lrelease not found.", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    ASSETS_TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)

    source_files = find_source_files()
    if not source_files:
        print("No source files found.")
        return 1

    lupdate = lupdate_cmd()
    lrelease = lrelease_cmd()

    for lang in LANGUAGES:
        ts_path = TRANSLATIONS_DIR / f"xfinaudio_{lang}.ts"
        qm_path = ASSETS_TRANSLATIONS_DIR / f"xfinaudio_{lang}.qm"

        print(f"Updating {ts_path.name} ...")
        cmd = lupdate + [str(f) for f in source_files] + ["-ts", str(ts_path), "-no-obsolete"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return result.returncode
        print(result.stdout.strip())

        print(f"Compiling {qm_path.name} ...")
        cmd = lrelease + [str(ts_path), "-qm", str(qm_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return result.returncode
        print(result.stdout.strip())

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
