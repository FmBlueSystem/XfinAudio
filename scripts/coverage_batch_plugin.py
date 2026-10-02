"""Structured pytest collection/execution evidence for the explicit batch gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_executed: set[str] = set()


def pytest_addoption(parser):
    parser.addoption("--xfin-collection-output", default=None)
    parser.addoption("--xfin-expected-collection", default=None)


def pytest_collection_finish(session):
    output = session.config.getoption("xfin_collection_output")
    if not output:
        return
    items = [
        {"nodeid": item.nodeid, "file": item.path.relative_to(session.config.rootpath).as_posix()}
        for item in session.items
    ]
    Path(output).write_text(json.dumps(items), encoding="utf-8")
    expected = session.config.getoption("xfin_expected_collection")
    if expected:
        wanted = json.loads(Path(expected).read_text(encoding="utf-8"))
        if items != wanted or session.config.option.collectonly:
            raise pytest.UsageError("Coverage batch collection differs from the complete manifest")


def pytest_runtest_logreport(report):
    if report.when == "setup":
        _executed.add(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    output = session.config.getoption("xfin_collection_output")
    expected = session.config.getoption("xfin_expected_collection")
    if not output or not expected:
        return
    wanted = json.loads(Path(expected).read_text(encoding="utf-8"))
    if exitstatus == 0 and _executed != {item["nodeid"] for item in wanted}:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    Path(output + ".run.json").write_text(
        json.dumps({"exitStatus": int(session.exitstatus), "executed": sorted(_executed)}), encoding="utf-8"
    )
