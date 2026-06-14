#!/usr/bin/env python3
"""Run or list non-audio release readiness gates for XfinAudio."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReleaseGateError(RuntimeError):
    """Raised when a release gate fails outside subprocess execution."""


class CommandGate(NamedTuple):
    """A release gate backed by a shell-free subprocess command."""

    name: str
    command: list[str]


NON_AUDIO_COMMAND_GATES = [
    CommandGate("tests", ["uv", "run", "pytest", "-q"]),
    CommandGate("type-check", ["uv", "run", "pyright", "src", "tests"]),
    CommandGate("coverage", ["uv", "run", "pytest", "--cov", "--cov-fail-under=70", "-q"]),
    CommandGate("lint", ["uv", "run", "ruff", "check", "."]),
    CommandGate("format", ["uv", "run", "ruff", "format", "--check", "."]),
    CommandGate(
        "release readiness smoke",
        ["uv", "run", "python", "scripts/smoke_release_readiness.py"],
    ),
    CommandGate(
        "open-source publication docs",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/test_open_source_license_docs.py",
            "tests/test_public_open_source_docs.py",
            "tests/test_github_community_templates.py",
            "tests/test_repository_publication_checklist.py",
            "tests/test_harmonic_mixing_doc.py",
        ],
    ),
    CommandGate(
        "publication artifact hygiene",
        ["uv", "run", "pytest", "-q", "tests/test_publication_artifact_hygiene.py"],
    ),
    CommandGate(
        "source package hygiene",
        ["uv", "run", "python", "scripts/source_package_hygiene_check.py"],
    ),
    CommandGate(
        "PyInstaller check-only",
        ["uv", "run", "python", "scripts/pyinstaller_build_smoke.py", "--check-only"],
    ),
]
PACKAGING_BUILD_GATE = CommandGate(
    "packaging temp build + launch/warning triage",
    [
        "uv",
        "run",
        "python",
        "scripts/pyinstaller_build_smoke.py",
        "--build-temp",
        "--validate-launch",
    ],
)
MANUAL_GATE_NAMES = [
    "real Mixed In Key audio QA",
]
MIK_QA_EVIDENCE_PATH = PROJECT_ROOT / "docs" / "qa-manual-mik-evidence.md"
MIK_QA_COMPLETED_MARKER = "<!-- MIK-QA-STATUS: completed -->"


def _mik_qa_evidence_status() -> str:
    """Return 'completed' if the manual MIK QA evidence file is marked complete."""
    if not MIK_QA_EVIDENCE_PATH.exists():
        return "pending_manual"
    content = MIK_QA_EVIDENCE_PATH.read_text(encoding="utf-8")
    return "completed" if MIK_QA_COMPLETED_MARKER in content else "pending_manual"


MANUAL_GATES = [
    f"{gate}: {'COMPLETED' if _mik_qa_evidence_status() == 'completed' else 'PENDING MANUAL'}"
    for gate in MANUAL_GATE_NAMES
]
LIMITATIONS = [
    "Automated tests and fixtures do not prove real Mixed In Key audio QA; see docs/qa-manual-mik-evidence.md.",
]


def command_text(command: Sequence[str]) -> str:
    """Return a readable command string for output."""
    return " ".join(command)


def check_root_artifact_hygiene(project_root: Path = PROJECT_ROOT) -> None:
    """Ensure PyInstaller root build artifacts are absent."""
    offenders = [path.name for path in (project_root / "build", project_root / "dist") if path.exists()]
    if offenders:
        offender_text = ", ".join(offenders)
        raise ReleaseGateError(f"Root artifact hygiene failed: project-root {offender_text} present")


def gate_evidence(
    name: str,
    command: Sequence[str] | None,
    status: str,
    return_code: int | None,
) -> dict[str, Any]:
    """Build one stable JSON gate evidence object."""
    return {
        "name": name,
        "command": list(command or []),
        "status": status,
        "return_code": return_code,
    }


def manual_gate_evidence() -> list[dict[str, str]]:
    """Build manual release gate evidence with current status."""
    return [{"name": gate_name, "status": _mik_qa_evidence_status()} for gate_name in MANUAL_GATE_NAMES]


def build_report(mode: str, gates: list[dict[str, Any]], overall_status: str) -> dict[str, Any]:
    """Build the release gate JSON evidence report."""
    return {
        "schema_version": 1,
        "mode": mode,
        "project_root": str(PROJECT_ROOT),
        "gates": gates,
        "manual_gates": manual_gate_evidence(),
        "overall_status": overall_status,
        "limitations": LIMITATIONS,
    }


def assert_report_path_will_not_create_root_artifact_dir(report_path: Path) -> None:
    """Reject report paths that would create project-root build/ or dist/."""
    absolute_report_path = report_path.expanduser().resolve(strict=False)
    for artifact_dir_name in ("build", "dist"):
        artifact_dir = PROJECT_ROOT / artifact_dir_name
        try:
            absolute_report_path.relative_to(artifact_dir)
        except ValueError:
            continue
        raise ReleaseGateError(
            f"Refusing to create report path under project-root {artifact_dir_name}/ artifact directory"
        )


def write_report_json(report_path: Path, report: dict[str, Any]) -> None:
    """Persist JSON evidence, creating non-root-artifact parent directories as needed."""
    assert_report_path_will_not_create_root_artifact_dir(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_listed_gates(include_packaging_build: bool) -> list[dict[str, Any]]:
    """Build listed gate evidence without running subprocesses."""
    gates = [gate_evidence(gate.name, gate.command, "listed", None) for gate in NON_AUDIO_COMMAND_GATES]
    gates.append(gate_evidence("root artifact hygiene", None, "listed", None))
    if include_packaging_build:
        gates.append(gate_evidence(PACKAGING_BUILD_GATE.name, PACKAGING_BUILD_GATE.command, "listed", None))
    return gates


def print_checklist(include_packaging_build: bool) -> None:
    """Print the release gates without executing subprocess commands."""
    print("CHECK-ONLY automated non-audio release gates")
    for gate in NON_AUDIO_COMMAND_GATES:
        print(f"- {gate.name}: {command_text(gate.command)}")
    print("- root artifact hygiene: project-root build/ and dist/ must be absent")
    if include_packaging_build:
        print(f"- optional {PACKAGING_BUILD_GATE.name}: {command_text(PACKAGING_BUILD_GATE.command)}")
    else:
        print(f"- optional {PACKAGING_BUILD_GATE.name}: add --include-packaging-build to execute")
    print("Manual/pending release gates")
    for gate in MANUAL_GATES:
        print(f"- {gate}")


def run_command_gate(gate: CommandGate) -> int:
    """Run one command gate and return its process exit code."""
    print(f"RUN {gate.name}: {command_text(gate.command)}", flush=True)
    result = subprocess.run(gate.command, cwd=PROJECT_ROOT, text=True)
    if result.returncode != 0:
        print(f"FAIL {gate.name} exited with {result.returncode}")
        return result.returncode
    print(f"PASS {gate.name}")
    return 0


def run_gates(include_packaging_build: bool, report_path: Path | None = None) -> int:
    """Run automated non-audio release gates and propagate the first failure."""
    mode = "include-packaging-build" if include_packaging_build else "run"
    report_gates: list[dict[str, Any]] = []

    for gate in NON_AUDIO_COMMAND_GATES:
        result = run_command_gate(gate)
        status = "passed" if result == 0 else "failed"
        report_gates.append(gate_evidence(gate.name, gate.command, status, result))
        if result != 0:
            if report_path is not None:
                write_report_json(report_path, build_report(mode, report_gates, "failed"))
            return result

    try:
        check_root_artifact_hygiene()
    except ReleaseGateError as error:
        print(f"FAIL root artifact hygiene: {error}")
        report_gates.append(gate_evidence("root artifact hygiene", None, "failed", 1))
        if report_path is not None:
            write_report_json(report_path, build_report(mode, report_gates, "failed"))
        return 1
    print("PASS root artifact hygiene: project-root build/ and dist/ are absent")
    report_gates.append(gate_evidence("root artifact hygiene", None, "passed", 0))

    if include_packaging_build:
        result = run_command_gate(PACKAGING_BUILD_GATE)
        status = "passed" if result == 0 else "failed"
        report_gates.append(gate_evidence(PACKAGING_BUILD_GATE.name, PACKAGING_BUILD_GATE.command, status, result))
        if result != 0:
            if report_path is not None:
                write_report_json(report_path, build_report(mode, report_gates, "failed"))
            return result

    print("Manual/pending release gates")
    for gate in MANUAL_GATES:
        print(f"- {gate}")
    if report_path is not None:
        write_report_json(report_path, build_report(mode, report_gates, "passed"))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse release gate runner arguments."""
    parser = argparse.ArgumentParser(description="Run or list XfinAudio non-audio release readiness gates.")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="List automated and manual gates without running subprocess checks. This is the default.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run non-audio automated gates except the optional temp packaging build.",
    )
    parser.add_argument(
        "--include-packaging-build",
        action="store_true",
        help="Run the PyInstaller temp build + launch/warning triage gate.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Write structured JSON evidence for listed or executed non-audio release gates.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run or list release readiness gates."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.check_only or not (args.run or args.include_packaging_build):
        print_checklist(include_packaging_build=args.include_packaging_build)
        if args.report_json is not None:
            write_report_json(
                args.report_json,
                build_report("check-only", build_listed_gates(args.include_packaging_build), "listed"),
            )
        return 0
    return run_gates(include_packaging_build=args.include_packaging_build, report_path=args.report_json)


if __name__ == "__main__":
    raise SystemExit(main())
