"""The migration source candidate has coherent metadata without relabeling binaries."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_migration_candidate_versions_and_source_notes_agree() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    own_package = next(item for item in lock["package"] if item["name"] == "xfinaudio")
    electron = json.loads((ROOT / "desktop-electron/package.json").read_text())
    npm_lock = json.loads((ROOT / "desktop-electron/package-lock.json").read_text())
    assert project["version"] == "2.3.1"
    assert own_package["version"] == project["version"]
    assert electron["version"] == project["version"]
    assert npm_lock["version"] == electron["version"]
    assert npm_lock["packages"][""]["version"] == electron["version"]
    notes = (ROOT / "docs/release-notes-v2.3.1.md").read_text()
    assert "unreleased beta/source candidate" in notes
    assert "V12" in notes and "not rebuilt or relabeled" in notes
    assert "docs/release-notes-v2.3.1.md" in (ROOT / "README.md").read_text()
