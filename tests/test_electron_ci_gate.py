"""Migration CI must execute both suites and reject incomplete Node evidence."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def gate():
    spec = importlib.util.spec_from_file_location("electron_ci_check", ROOT / "scripts/electron_ci_check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summary(**overrides):
    counts = {"tests": 3, "pass": 3, "fail": 0, "cancelled": 0, "skipped": 0, "todo": 0}
    counts.update(overrides)
    return "TAP version 13\n" + "".join(f"# {name} {value}\n" for name, value in counts.items())


@pytest.mark.parametrize("count", [1, 37, 500])
def test_complete_summary_does_not_hardcode_test_count(count):
    assert gate().parse_summary(summary(tests=count, **{"pass": count}))["tests"] == count


@pytest.mark.parametrize(
    "output",
    [
        "",
        "# tests 3\n# pass 3\n",
        summary(tests=0, **{"pass": 0}),
        summary(**{"pass": 2}),
        summary(**{"pass": 2, "fail": 1}),
        summary(**{"pass": 2, "skipped": 1}),
        summary(**{"pass": 2, "cancelled": 1}),
        summary(**{"pass": 2, "todo": 1}),
        summary() + "# tests 3\n",
        summary() + "# tests NaN\n",
        summary() + "# skipped -1\n",
    ],
)
def test_missing_failed_skipped_cancelled_todo_or_inconsistent_summary_fails(output):
    with pytest.raises(ValueError):
        gate().parse_summary(output)


@pytest.mark.parametrize("code,output,expected", [(0, summary(), 0), (7, summary(), 7), (0, summary(skipped=1), 1)])
def test_runner_executes_npm_test_and_records_actual_outcome(tmp_path, monkeypatch, code, output, expected):
    module = gate()
    monkeypatch.setenv("XFIN_PYTHON", "/isolated/bin/python")
    calls = []

    def execute(command, *, cwd, env, log, timeout):
        calls.append(command)
        assert env["XFIN_PYTHON"] == "/isolated/bin/python"
        assert env["NODE_OPTIONS"] == "--test-reporter=tap"
        assert timeout <= 600
        log.write(output if command == ["npm", "test"] else "Qt-free preflight\n")
        return code if command == ["npm", "test"] else 0

    monkeypatch.setattr(module, "execute", execute)
    assert module.run(tmp_path, tmp_path / "evidence") == expected
    assert calls[0][:2] == ["/isolated/bin/python", "-I"]
    assert "PySide6" in calls[0][3] and "PyQt6" in calls[0][3]
    assert calls[1] == ["npm", "test"]
    report = json.loads((tmp_path / "evidence/electron-test-report.json").read_text())
    assert report["status"] == ("passed" if expected == 0 else "failed")
    assert report["returnCode"] == code
    assert report["summary"]["skipped"] == (1 if expected == 1 else 0)
    assert output in (tmp_path / "evidence/electron-test.log").read_text()


def test_missing_interpreter_cannot_skip_integrations_and_pass(tmp_path, monkeypatch):
    module = gate()
    monkeypatch.delenv("XFIN_PYTHON", raising=False)
    monkeypatch.setattr(module, "execute", lambda *args, **kwargs: pytest.fail("must not run without interpreter"))
    assert module.run(tmp_path, tmp_path / "evidence") == 1
    report = json.loads((tmp_path / "evidence/electron-test-report.json").read_text())
    assert report["status"] == "failed" and "XFIN_PYTHON" in report["error"]


@pytest.mark.parametrize("failure", [OSError("missing executable"), subprocess.TimeoutExpired("npm test", 600)])
def test_start_failure_or_timeout_retains_failed_evidence(tmp_path, monkeypatch, failure):
    module = gate()
    monkeypatch.setenv("XFIN_PYTHON", "/isolated/bin/python")

    def execute(*args, **kwargs):
        raise failure

    monkeypatch.setattr(module, "execute", execute)
    assert module.run(tmp_path, tmp_path / "evidence") == 1
    report = json.loads((tmp_path / "evidence/electron-test-report.json").read_text())
    assert report["status"] == "failed" and report["error"]


def test_failed_interpreter_preflight_never_starts_npm(tmp_path, monkeypatch):
    module = gate()
    monkeypatch.setenv("XFIN_PYTHON", "/isolated/bin/python")
    calls = []
    monkeypatch.setattr(module, "execute", lambda command, **kwargs: calls.append(command) or 13)
    assert module.run(tmp_path, tmp_path / "evidence") == 1
    assert len(calls) == 1 and calls[0][0] == "/isolated/bin/python"
    report = json.loads((tmp_path / "evidence/electron-test-report.json").read_text())
    assert report["preflightReturnCode"] == 13 and report["returnCode"] is None


def test_subprocess_return_code_and_combined_log_are_real(tmp_path):
    with (tmp_path / "log").open("w") as log:
        result = gate().execute(
            [sys.executable, "-c", "import sys; print('stdout'); print('stderr', file=sys.stderr); sys.exit(7)"],
            cwd=tmp_path,
            env=None,
            log=log,
            timeout=5,
        )
    assert result == 7
    assert {"stdout", "stderr"} <= set((tmp_path / "log").read_text().splitlines())


def test_subprocess_timeout_is_enforced(tmp_path):
    with (tmp_path / "log").open("w") as log, pytest.raises(subprocess.TimeoutExpired):
        gate().execute(
            [sys.executable, "-c", "import time; time.sleep(30)"], cwd=tmp_path, env=None, log=log, timeout=0.1
        )


def test_workflow_runs_complete_sharded_aggregate_and_keeps_manifest_evidence():
    workflow = (ROOT / ".github/workflows/non-audio-release-gates.yml").read_text()
    assert workflow.count("--coverage-batch-size 120") == 2
    assert workflow.count('--coverage-evidence-dir "${{ runner.temp }}/coverage-evidence"') == 2
    assert "${{ runner.temp }}/coverage-evidence/" in workflow
    assert "include-hidden-files: true" in workflow
    assert "--cov-fail-under" not in workflow
    assert "uv sync --locked" in workflow


def test_electron_job_installs_public_locked_dependencies_and_runs_real_gate():
    workflow = (ROOT / ".github/workflows/non-audio-release-gates.yml").read_text()
    assert "electron-migration-tests:" in workflow
    assert "actions/setup-node@2028fbc5c25fe9cf00d9f06a71cc4710d4507903 # v6.0.0" in workflow
    assert 'node-version: "24.19.0"' in workflow
    assert 'uv venv "${{ runner.temp }}/electron-python" --python 3.12' in workflow
    assert 'uv pip sync --python "${{ runner.temp }}/electron-python/bin/python"' in workflow
    assert "--require-hashes --index-url https://pypi.org/simple" in workflow
    assert "desktop-electron/requirements-headless.txt" in workflow
    assert "npm ci --registry=https://registry.npmjs.org" in workflow
    assert "XFIN_PYTHON: ${{ runner.temp }}/electron-python/bin/python" in workflow
    assert "scripts/electron_ci_check.py" in workflow
    assert "command -v ffmpeg" in workflow
    assert "electron-test-report.json" in workflow and "electron-test.log" in workflow
    assert "steps.electron-tests.outcome" in workflow
    assert "continue-on-error" not in workflow


@pytest.mark.parametrize("job_name", ["non-audio-release-gates", "electron-migration-tests"])
def test_each_hosted_job_provisions_and_probes_ffmpeg_before_test_execution(job_name):
    workflow = (ROOT / ".github/workflows/non-audio-release-gates.yml").read_text()
    job = workflow.split(f"\n  {job_name}:\n", 1)[1].split("\n  electron-migration-tests:\n", 1)[0]
    prerequisite = (
        "      - name: Ensure FFmpeg integration prerequisite\n"
        "        run: |\n"
        "          if ! command -v ffmpeg >/dev/null; then brew install ffmpeg; fi\n"
        "          ffmpeg -version\n"
    )
    assert job.count(prerequisite) == 1
    test_gate = (
        "scripts/release_gate_check.py" if job_name == "non-audio-release-gates" else "scripts/electron_ci_check.py"
    )
    assert job.index(prerequisite) < job.index(test_gate)


def test_electron_interpreter_uses_runner_context_only_at_the_suite_step():
    workflow = (ROOT / ".github/workflows/non-audio-release-gates.yml").read_text()
    electron_job = workflow.split("\n  electron-migration-tests:\n", 1)[1]
    job_configuration, steps = electron_job.split("\n    steps:\n", 1)
    # runner is unavailable in job-level env but allowed in steps.env:
    # https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability
    assert "${{ runner." not in job_configuration
    suite_step = steps.split("      - name: Run Electron suite with zero-skip evidence\n", 1)[1]
    suite_step = suite_step.split("\n      - name:", 1)[0]
    assert "\n        env:\n          XFIN_PYTHON: ${{ runner.temp }}/electron-python/bin/python\n" in suite_step
    assert "run: '\"$XFIN_PYTHON\" scripts/electron_ci_check.py'" in suite_step


@pytest.mark.parametrize("artifact", ["non-audio-release-gate-evidence", "electron-test-evidence"])
def test_each_evidence_upload_includes_its_explicit_hidden_paths(artifact):
    workflow = (ROOT / ".github/workflows/non-audio-release-gates.yml").read_text()
    upload = workflow.split(f"name: {artifact}\n", 1)[1].split("if-no-files-found: error", 1)[0]
    assert "include-hidden-files: true" in upload
    paths = upload.split("path: |\n", 1)[1].splitlines()
    assert paths and all(
        line.strip().startswith(".release-evidence/") or line.strip() == "${{ runner.temp }}/coverage-evidence/"
        for line in paths
        if line.strip()
    )
