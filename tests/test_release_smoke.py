"""Release readiness smoke script tests."""

from __future__ import annotations

import subprocess
import sys

EXPECTED_PASS_LINES = [
    "PASS temp app database created",
    "PASS track repository saved and listed fixtures",
    "PASS playlist workflow recommendation built",
    "PASS playlist exporters produced JSON/CSV/M3U strings",
    "PASS quality report JSON built",
    "PASS DJ readiness:",
    "PASS Serato crate dry-run plan built without writing",
    "PASS release readiness smoke completed",
]


def test_release_readiness_smoke_script_prints_checklist() -> None:
    """The release smoke script runs end-to-end and prints a concise pass checklist."""
    result = subprocess.run(
        [sys.executable, "scripts/smoke_release_readiness.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    for line in EXPECTED_PASS_LINES:
        assert line in result.stdout
    assert "FAIL" not in result.stdout
