"""Keep the manual migration inventory aligned with committed dependency locks."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "third-party-license-inventory.md"


def inventory_rows(heading: str) -> dict[str, list[str]]:
    """Read a named supplement table without depending on installed packages."""
    text = INVENTORY.read_text(encoding="utf-8")
    assert heading in text, f"Missing migration inventory section: {heading}"
    section = text.split(heading, 1)[1].split("\n##", 1)[0]
    rows = {}
    for line in section.splitlines():
        if line.startswith("| `"):
            cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
            assert cells[0] not in rows, f"Duplicate inventory row: {cells[0]}"
            rows[cells[0]] = cells[1:]
    return rows


def test_migration_inventory_covers_every_headless_lock_pin() -> None:
    locked = (ROOT / "desktop-electron" / "requirements-headless.txt").read_text(encoding="utf-8")
    pins = dict(re.findall(r"^([A-Za-z0-9._-]+)==([^\s\\]+)", locked, re.MULTILINE))
    rows = inventory_rows("### Hash-locked headless Python dependencies")

    assert rows.keys() == pins.keys()
    for name, version in pins.items():
        assert rows[name][0] == version
        assert rows[name][1], f"Missing license evidence or explicit uncertainty for {name}"


def test_migration_inventory_covers_every_npm_lock_record() -> None:
    lock = json.loads((ROOT / "desktop-electron" / "package-lock.json").read_text(encoding="utf-8"))
    packages = {name: data for name, data in lock["packages"].items() if name}
    rows = inventory_rows("### npm lock metadata")

    assert rows.keys() == packages.keys()
    for name, data in packages.items():
        assert rows[name][:2] == [data["version"], data["license"]]
        assert data["integrity"].startswith("sha512-")


def test_inventory_preserves_legacy_scope_and_binary_review_boundary() -> None:
    text = INVENTORY.read_text(encoding="utf-8")

    assert "## Legacy direct-Python snapshot" in text
    assert "PySide6" not in text, "Qt/PySide6 is no longer a dependency of XfinAudio"
    assert "| mutagen | 1.47.0 |" in text
    assert "## Legacy bundled FFmpeg CLI provenance" in text
    assert "not a complete binary bill of materials" in text
    assert "a nonempty dependency-license directory does not prove coverage" in text
    assert "No legal clearance or binary redistribution approval" in text
    assert "does not generate the migration supplement" in text
