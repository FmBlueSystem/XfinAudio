"""Automated non-audio release gate runner tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_GATE_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "release_gate_check.py"
RELEASE_READINESS_DOC = PROJECT_ROOT / "docs" / "release-readiness-smoke.md"
PACKAGING_STRATEGY_DOC = PROJECT_ROOT / "docs" / "packaging-strategy.md"
RELEASE_EVIDENCE_DOC = PROJECT_ROOT / "docs" / "release-candidate-evidence.md"
OPEN_SOURCE_RELEASE_BACKLOG_DOC = PROJECT_ROOT / "docs" / "open-source-release-backlog.md"

_release_gate_spec = importlib.util.spec_from_file_location("release_gate_check", RELEASE_GATE_SCRIPT_PATH)
assert _release_gate_spec is not None
assert _release_gate_spec.loader is not None
release_gate_check = importlib.util.module_from_spec(_release_gate_spec)
_release_gate_spec.loader.exec_module(release_gate_check)


def test_default_check_only_lists_non_audio_gates_without_running_commands(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)

    assert release_gate_check.main([]) == 0

    output = capsys.readouterr().out
    assert calls == []
    assert "CHECK-ONLY automated non-audio release gates" in output
    assert "uv run pytest -q" in output
    assert "uv run ruff check ." in output
    assert "uv run ruff format --check ." in output
    assert (
        "uv run pytest -q tests/test_open_source_license_docs.py tests/test_public_open_source_docs.py "
        "tests/test_github_community_templates.py tests/test_repository_publication_checklist.py "
        "tests/test_harmonic_mixing_doc.py" in output
    )
    assert "uv run pytest -q tests/test_publication_artifact_hygiene.py" in output
    assert "uv run python scripts/source_package_hygiene_check.py" in output
    assert "uv run python scripts/pyinstaller_build_smoke.py --check-only" in output
    assert "root artifact hygiene: project-root build/ and dist/ must be absent" in output
    assert "real Mixed In Key audio QA: PENDING MANUAL" in output


def test_check_only_with_include_packaging_build_lists_optional_command_without_running(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)

    assert release_gate_check.main(["--check-only", "--include-packaging-build"]) == 0

    output = capsys.readouterr().out
    assert calls == []
    assert "optional packaging temp build + launch/warning triage" in output
    assert "uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch" in output


def test_include_packaging_build_adds_temp_launch_validation_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)
    monkeypatch.setattr(release_gate_check, "check_root_artifact_hygiene", lambda: None)

    assert release_gate_check.main(["--include-packaging-build"]) == 0

    assert calls[-1] == [
        "uv",
        "run",
        "python",
        "scripts/pyinstaller_build_smoke.py",
        "--build-temp",
        "--validate-launch",
    ]
    output = capsys.readouterr().out
    assert "PASS packaging temp build + launch/warning triage" in output


def test_run_mode_propagates_subprocess_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return_code = 17 if command == ["uv", "run", "ruff", "check", "."] else 0
        return subprocess.CompletedProcess(command, return_code)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)
    monkeypatch.setattr(release_gate_check, "check_root_artifact_hygiene", lambda: None)

    assert release_gate_check.main(["--run"]) == 17

    assert calls == [
        ["uv", "run", "pytest", "-q"],
        ["uv", "run", "ruff", "check", "."],
    ]
    output = capsys.readouterr().out
    assert "FAIL lint exited with 17" in output
    assert "uv run ruff format --check ." not in output


def test_root_artifact_hygiene_fails_when_build_or_dist_exists(tmp_path: Path) -> None:
    (tmp_path / "build").mkdir()

    with pytest.raises(release_gate_check.ReleaseGateError, match="Root artifact hygiene failed"):
        release_gate_check.check_root_artifact_hygiene(tmp_path)


def test_report_json_refuses_project_root_build_or_dist_artifact_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(release_gate_check, "PROJECT_ROOT", tmp_path)

    for artifact_dir_name in ("build", "dist"):
        artifact_dir = tmp_path / artifact_dir_name
        report_path = artifact_dir / "release-gate-report.json"

        with pytest.raises(release_gate_check.ReleaseGateError, match="Refusing to create report path"):
            release_gate_check.write_report_json(report_path, {"schema_version": 1})
        assert not artifact_dir.exists()

        artifact_dir.mkdir()
        with pytest.raises(release_gate_check.ReleaseGateError, match="Refusing to create report path"):
            release_gate_check.write_report_json(report_path, {"schema_version": 1})
        assert not report_path.exists()

    assert not (PROJECT_ROOT / "build").exists()
    assert not (PROJECT_ROOT / "dist").exists()


def test_check_only_report_json_lists_gates_and_pending_manual_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)
    report_path = tmp_path / "nested" / "release-gate-report.json"

    assert release_gate_check.main(["--check-only", "--report-json", str(report_path)]) == 0

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert calls == []
    assert report["schema_version"] == 1
    assert report["mode"] == "check-only"
    assert report["project_root"] == str(PROJECT_ROOT)
    assert report["overall_status"] == "listed"
    assert {gate["name"]: gate["status"] for gate in report["gates"]} == {
        "tests": "listed",
        "lint": "listed",
        "format": "listed",
        "open-source publication docs": "listed",
        "publication artifact hygiene": "listed",
        "source package hygiene": "listed",
        "PyInstaller check-only": "listed",
        "root artifact hygiene": "listed",
    }
    assert report["gates"][0]["command"] == ["uv", "run", "pytest", "-q"]
    open_source_gate = next(gate for gate in report["gates"] if gate["name"] == "open-source publication docs")
    assert open_source_gate["command"] == [
        "uv",
        "run",
        "pytest",
        "-q",
        "tests/test_open_source_license_docs.py",
        "tests/test_public_open_source_docs.py",
        "tests/test_github_community_templates.py",
        "tests/test_repository_publication_checklist.py",
        "tests/test_harmonic_mixing_doc.py",
    ]
    assert all(gate["return_code"] is None for gate in report["gates"])
    assert report["manual_gates"] == [
        {"name": "real Mixed In Key audio QA", "status": "pending_manual"},
    ]
    assert "Does not prove real Mixed In Key audio QA" in report["limitations"]


def test_successful_run_report_json_records_passed_gates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)
    monkeypatch.setattr(release_gate_check, "check_root_artifact_hygiene", lambda: None)
    report_path = tmp_path / "release-gate-report.json"

    assert release_gate_check.main(["--run", "--report-json", str(report_path)]) == 0

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "run"
    assert report["overall_status"] == "passed"
    assert {gate["name"]: (gate["status"], gate["return_code"]) for gate in report["gates"]} == {
        "tests": ("passed", 0),
        "lint": ("passed", 0),
        "format": ("passed", 0),
        "open-source publication docs": ("passed", 0),
        "publication artifact hygiene": ("passed", 0),
        "source package hygiene": ("passed", 0),
        "PyInstaller check-only": ("passed", 0),
        "root artifact hygiene": ("passed", 0),
    }
    assert calls == [gate.command for gate in release_gate_check.NON_AUDIO_COMMAND_GATES]


def test_failure_report_json_is_written_before_nonzero_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return_code = 17 if command == ["uv", "run", "ruff", "check", "."] else 0
        return subprocess.CompletedProcess(command, return_code)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)
    report_path = tmp_path / "release-gate-report.json"

    assert release_gate_check.main(["--run", "--report-json", str(report_path)]) == 17

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["overall_status"] == "failed"
    assert [(gate["name"], gate["status"], gate["return_code"]) for gate in report["gates"]] == [
        ("tests", "passed", 0),
        ("lint", "failed", 17),
    ]
    assert report["manual_gates"][0] == {"name": "real Mixed In Key audio QA", "status": "pending_manual"}


def test_include_packaging_build_report_json_includes_optional_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(release_gate_check.subprocess, "run", fake_run)
    monkeypatch.setattr(release_gate_check, "check_root_artifact_hygiene", lambda: None)
    report_path = tmp_path / "release-gate-report.json"

    assert release_gate_check.main(["--include-packaging-build", "--report-json", str(report_path)]) == 0

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "include-packaging-build"
    assert report["overall_status"] == "passed"
    assert report["gates"][-1] == {
        "name": "packaging temp build + launch/warning triage",
        "command": [
            "uv",
            "run",
            "python",
            "scripts/pyinstaller_build_smoke.py",
            "--build-temp",
            "--validate-launch",
        ],
        "status": "passed",
        "return_code": 0,
    }


def test_release_docs_reference_non_audio_gate_runner_and_limits() -> None:
    docs = [
        RELEASE_READINESS_DOC.read_text(encoding="utf-8"),
        PACKAGING_STRATEGY_DOC.read_text(encoding="utf-8"),
        RELEASE_EVIDENCE_DOC.read_text(encoding="utf-8"),
        OPEN_SOURCE_RELEASE_BACKLOG_DOC.read_text(encoding="utf-8"),
    ]

    for doc_text in docs:
        assert "scripts/release_gate_check.py" in doc_text

    readiness_text = docs[0]
    assert "uv run python scripts/release_gate_check.py --run" in readiness_text
    assert (
        "uv run python scripts/release_gate_check.py --run --report-json /tmp/xfinaudio-release-gate-report.json"
        in readiness_text
    )
    assert "uv run python scripts/release_gate_check.py --include-packaging-build" in readiness_text
    assert "does not require audio files" in readiness_text
    assert "cannot prove real Mixed In Key audio QA" in readiness_text
    assert "The equivalent individual commands are:" not in readiness_text
    assert "Individual automated gate commands" in readiness_text
    assert "Additional non-audio smoke command" in readiness_text
    assert "Manual desktop launch command" in readiness_text
    assert "open-source publication docs" in readiness_text
    assert "publication artifact hygiene" in readiness_text
    assert "source package hygiene" in readiness_text
    assert "uv run python scripts/source_package_hygiene_check.py" in readiness_text

    assert ".release-evidence/release-gate-report.json" in readiness_text
    assert ".release-evidence/release-gate-evidence.md" in readiness_text
    assert "both JSON report and Markdown snippet" in readiness_text

    packaging_text = docs[1]
    assert "renders `.release-evidence/release-gate-evidence.md`" in packaging_text
    assert "uploads both JSON and Markdown evidence files" in packaging_text
    assert "open-source publication docs" in packaging_text
    assert "publication artifact hygiene" in packaging_text
    assert "source package hygiene" in packaging_text

    evidence_text = docs[2]
    assert "Non-audio release gate runner" in evidence_text
    assert "--report-json PATH" in evidence_text
    assert "open-source publication docs" in evidence_text
    assert "publication artifact hygiene" in evidence_text
    assert "source package hygiene" in evidence_text
    assert "non-audio-release-gate-evidence" in evidence_text
    assert "non-audio-release-gate-report" not in evidence_text
    assert "Manual audio QA remains pending" in evidence_text
    assert "harmonic mixing guide" in evidence_text
    assert "Source publication readiness refresh" in evidence_text
    assert "230 passed" in evidence_text
    assert "open-source publication docs" in evidence_text
    assert "publication artifact hygiene" in evidence_text
