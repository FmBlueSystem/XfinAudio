#!/usr/bin/env python3
"""Run the actual Electron npm suite and retain fail-closed, zero-skip evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COUNTERS = ("tests", "pass", "fail", "cancelled", "skipped", "todo")


def summary_counts(output: str) -> dict[str, int]:
    """Require one complete Node TAP summary; never infer an expected count."""
    counts = {}
    for key in COUNTERS:
        values = re.findall(rf"^# {key} (.*)$", output, re.MULTILINE)
        if len(values) != 1 or not values[0].isdigit():
            raise ValueError(f"Missing, invalid or duplicate Node summary counter: {key}")
        counts[key] = int(values[0])
    return counts


def parse_summary(output: str) -> dict[str, int]:
    counts = summary_counts(output)
    if counts["tests"] <= 0 or counts["pass"] != counts["tests"] or any(counts[key] for key in COUNTERS[2:]):
        raise ValueError(f"Incomplete or unsuccessful Node suite: {counts}")
    return counts


def execute(command, *, cwd, env, log, timeout):
    """Bound the entire subprocess group, including npm's shell and Node child."""
    with subprocess.Popen(
        command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    ) as process:
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise


def run(root: Path, evidence: Path) -> int:
    evidence.mkdir(parents=True, exist_ok=True)
    logfile = evidence / "electron-test.log"
    report: dict[str, Any] = {"status": "failed", "command": ["npm", "test"], "returnCode": None, "summary": {}}
    env = {**os.environ, "NODE_OPTIONS": "--test-reporter=tap"}
    result = 1
    try:
        with logfile.open("w", encoding="utf-8") as log:
            python = env.get("XFIN_PYTHON")
            if not python:
                raise ValueError("XFIN_PYTHON must select the separate locked Qt-free interpreter")
            preflight = [
                python,
                "-I",
                "-c",
                "import importlib.util; import mutagen, pydantic, numpy, librosa; "
                "assert all(importlib.util.find_spec(name) is None "
                "for name in ('PySide6', 'PySide2', 'PyQt6', 'PyQt5')), 'Qt runtime installed'; "
                "print('Qt-free Python preflight passed')",
            ]
            preflight_code = execute(preflight, cwd=root, env=env, log=log, timeout=60)
            report["preflightReturnCode"] = preflight_code
            if preflight_code:
                raise ValueError("Qt-free Python preflight failed")
            result = execute(report["command"], cwd=root / "desktop-electron", env=env, log=log, timeout=600)
            report["returnCode"] = result
        output = logfile.read_text(encoding="utf-8")
        report["summary"] = summary_counts(output)
        parse_summary(output)
        if result:
            raise ValueError(f"npm test failed with exit code {result}")
        report["status"] = "passed"
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
        result = result or 1
    (evidence / "electron-test-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(logfile.read_text(encoding="utf-8"), end="")
    print(json.dumps(report, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / ".release-evidence")
    return run(ROOT, parser.parse_args().evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())
