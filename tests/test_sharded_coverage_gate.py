"""The resource-isolated gate must run every test and keep the configured floor."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sharded_coverage_check.py"


def module():
    spec = importlib.util.spec_from_file_location("sharded_coverage_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_batches_keep_files_whole_and_cover_every_collected_identity_once():
    items = [{"file": "tests/a.py", "nodeid": f"tests/a.py::test_a[{i}]"} for i in range(3)]
    items += [{"file": "tests/b.py", "nodeid": "tests/b.py::test_b"}]
    batches = module().plan_batches(items, 2)
    assert batches == [items[:3], items[3:]]
    assert [item for batch in batches for item in batch] == items


@pytest.mark.parametrize("size", [0, -1, 1001, True, 1.5])
def test_invalid_batch_bounds_fail(size):
    with pytest.raises(ValueError):
        module().plan_batches([{"file": "tests/a.py", "nodeid": "tests/a.py::test_a"}], size)


@pytest.mark.parametrize(
    "items",
    [
        [],
        [{"file": "../outside", "nodeid": "x"}],
        [{"file": "/outside", "nodeid": "x"}],
        [{"file": "tests/a.py", "nodeid": "x"}] * 2,
    ],
)
def test_empty_duplicate_or_escaping_collection_is_rejected(items):
    with pytest.raises(ValueError):
        module().plan_batches(items, 20)


def project(tmp_path: Path, *, broken=False, uncovered=False, drift=False) -> Path:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths=["tests"]\npythonpath=["src"]\n[tool.coverage.run]\nsource=["src"]\n[tool.coverage.report]\nfail_under=100\n'
    )
    source = "def add(a,b):\n    return a+b\n"
    if uncovered:
        source += "def uncovered():\n    return 42\n"
    (root / "src" / "sample.py").write_text(source)
    (root / "tests" / "test_a.py").write_text(
        "from sample import add\ndef test_a():\n    assert add(1,2)==" + ("4" if broken else "3") + "\n"
    )
    (root / "tests" / "test_b.py").write_text("from sample import add\ndef test_b():\n    assert add(2,3)==5\n")
    if drift:
        (root / "tests" / "test_b.py").write_text(
            "from pathlib import Path\nfrom sample import add\ndef test_b():\n    assert add(2,3)==5\n"
            "    Path('src/sample.py').write_text('def add(a,b):\\n    return a+b+1\\n')\n"
        )
    return root


def run_project(root: Path, evidence: Path, **extra_env):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COV_CORE_") and key not in {"PYTEST_ADDOPTS", "COVERAGE_PROCESS_START"}
    }
    env.update(extra_env)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-root",
            str(root),
            "--evidence-dir",
            str(evidence),
            "--batch-size",
            "1",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=40,
    )


def test_real_tiny_suite_runs_every_batch_combines_isolated_data_and_keeps_full_evidence(tmp_path):
    root, evidence = project(tmp_path), tmp_path / "evidence"
    (root / ".coverage").write_bytes(b"stale unrelated coverage")
    result = run_project(root, evidence)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["status"] == "passed" and manifest["collectedCount"] == 2
    assert len(manifest["batches"]) == 2 and all(item["returnCode"] == 0 for item in manifest["batches"])
    assert (root / ".coverage").read_bytes() == b"stale unrelated coverage"
    assert "100%" in (evidence / "coverage-report.log").read_text()
    assert all("--cov-fail-under" not in " ".join(command) for command in manifest["commands"])


@pytest.mark.parametrize("reason", ["test_failure", "low_coverage", "source_drift"])
def test_failure_coverage_floor_and_changed_source_never_report_success(tmp_path, reason):
    root = project(
        tmp_path, broken=reason == "test_failure", uncovered=reason == "low_coverage", drift=reason == "source_drift"
    )
    evidence = tmp_path / "evidence"
    result = run_project(root, evidence)
    assert result.returncode != 0
    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["status"] == "failed"
    if reason == "test_failure":
        assert len(manifest["batches"]) == 1
    if reason == "low_coverage":
        assert "fail-under" in (evidence / "coverage-report.log").read_text()
    if reason == "source_drift":
        assert "changed" in manifest["error"].lower()


def test_inherited_selection_options_and_reused_evidence_are_rejected(tmp_path):
    root = project(tmp_path)
    evidence = tmp_path / "evidence"
    result = run_project(root, evidence, PYTEST_ADDOPTS="-k only_one")
    assert result.returncode != 0 and "PYTEST_ADDOPTS" in result.stdout + result.stderr
    evidence.mkdir(exist_ok=True)
    (evidence / "do-not-overwrite").write_text("fixture")
    result = run_project(root, evidence)
    assert result.returncode != 0
    assert (evidence / "do-not-overwrite").read_text() == "fixture"


def test_evidence_cannot_create_root_build_artifacts(tmp_path):
    root = project(tmp_path)
    result = run_project(root, root / "build" / "evidence")
    assert result.returncode != 0
    assert not (root / "build").exists()


@pytest.mark.parametrize("mode", ["collection_drift", "suppressed_execution"])
def test_changed_collection_or_unexecuted_tests_fail_before_coverage_report(tmp_path, mode):
    root = project(tmp_path)
    if mode == "collection_drift":
        hook = (
            "def pytest_collection_modifyitems(config,items):\n"
            "    if config.getoption('xfin_expected_collection'): items.clear()\n"
        )
    else:
        hook = (
            "def pytest_runtestloop(session):\n"
            "    if session.config.getoption('xfin_expected_collection'): return True\n"
        )
    (root / "conftest.py").write_text(hook)
    evidence = tmp_path / "evidence"
    result = run_project(root, evidence)
    assert result.returncode != 0
    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["status"] == "failed" and len(manifest["batches"]) == 1
    assert not (evidence / "coverage-report.log").exists()


@pytest.mark.parametrize("mode", ["missing", "invalid"])
def test_every_batch_must_produce_valid_coverage_data(tmp_path, mode):
    root = project(tmp_path)
    saving = (
        "lambda: None"
        if mode == "missing"
        else "lambda: Path(cov.config.data_file + '.fixture').write_bytes(b'invalid')"
    )
    (root / "tests" / "test_a.py").write_text(
        "from pathlib import Path\nimport coverage\nfrom sample import add\n"
        "def test_a():\n    assert add(1,2)==3\n    cov=coverage.Coverage.current()\n"
        f"    cov.save={saving}\n"
    )
    evidence = tmp_path / "evidence"
    result = run_project(root, evidence)
    assert result.returncode != 0
    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["status"] == "failed" and len(manifest["batches"]) == 1
    assert not (evidence / "coverage-report.log").exists()
