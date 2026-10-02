"""Opt-in aggregate batching changes only the coverage command, never defaults."""

import json
import subprocess

import pytest

from tests.test_release_gate_check import release_gate_check as gate


def test_sharded_check_only_records_selected_command_without_running_or_creating_evidence(
    tmp_path, monkeypatch, capsys
):
    calls = []
    monkeypatch.setattr(gate.subprocess, "run", lambda *args, **kwargs: calls.append(args))
    evidence, report = tmp_path / "coverage", tmp_path / "report.json"
    assert (
        gate.main(
            [
                "--check-only",
                "--coverage-batch-size",
                "180",
                "--coverage-evidence-dir",
                str(evidence),
                "--report-json",
                str(report),
            ]
        )
        == 0
    )
    assert calls == [] and not evidence.exists()
    data = json.loads(report.read_text())
    assert data["gates"][0]["command"] == [
        "uv",
        "run",
        "python",
        "scripts/sharded_coverage_check.py",
        "--batch-size",
        "180",
        "--evidence-dir",
        str(evidence),
    ]
    assert "sharded_coverage_check.py --batch-size 180" in capsys.readouterr().out
    assert data["gates"][1]["command"] == gate.NON_AUDIO_COMMAND_GATES[1].command
    assert gate.NON_AUDIO_COMMAND_GATES[0].command == ["uv", "run", "pytest", "--cov", "-q"]


def test_failed_sharded_coverage_stops_aggregate_and_keeps_command_evidence(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 17)

    monkeypatch.setattr(gate.subprocess, "run", run)
    report = tmp_path / "report.json"
    assert gate.main(["--run", "--coverage-batch-size", "180", "--report-json", str(report)]) == 17
    assert len(calls) == 1 and "scripts/sharded_coverage_check.py" in calls[0]
    data = json.loads(report.read_text())
    assert data["overall_status"] == "failed" and data["gates"][0]["return_code"] == 17


def test_successful_sharded_mode_retains_every_other_gate_and_manual_status(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(gate.subprocess, "run", run)
    monkeypatch.setattr(gate, "check_root_artifact_hygiene", lambda: None)
    report = tmp_path / "report.json"
    assert gate.main(["--run", "--coverage-batch-size", "100", "--report-json", str(report)]) == 0
    assert calls[1:] == [item.command for item in gate.NON_AUDIO_COMMAND_GATES[1:]]
    data = json.loads(report.read_text())
    assert data["overall_status"] == "passed" and data["manual_gates"] == gate.manual_gate_evidence()


@pytest.mark.parametrize(
    "arguments",
    [
        ["--coverage-batch-size", "0"],
        ["--coverage-batch-size", "1001"],
        ["--coverage-batch-size", "NaN"],
        ["--coverage-evidence-dir", "/tmp/unused"],
    ],
)
def test_bad_batch_configuration_is_rejected_before_running(arguments):
    with pytest.raises(SystemExit) as failure:
        gate.main(["--run", *arguments])
    assert failure.value.code == 2
