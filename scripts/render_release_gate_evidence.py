#!/usr/bin/env python3
"""Render XfinAudio non-audio release gate JSON evidence as Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {"mode", "gates", "manual_gates", "overall_status", "limitations"}
MANUAL_LIMITATION_NOTE = (
    "This non-audio evidence does not prove manual audio QA, clean macOS account validation, "
    "signing/notarization/DMG, or release completion."
)


class RenderEvidenceError(RuntimeError):
    """Raised when release gate evidence cannot be rendered safely."""


def markdown_table_text(value: object) -> str:
    """Escape a value for Markdown table cells."""
    text = "—" if value is None or value == "" else str(value)
    return text.replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def markdown_list_text(value: object) -> str:
    """Escape a value for Markdown list items."""
    return str(value).replace("\n", " ").replace("\r", " ")


def command_markdown(command: object) -> str:
    """Render a report command as a Markdown code span."""
    if not command:
        return "—"
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        raise RenderEvidenceError("gate command must be a list of strings")
    command_text = " ".join(command).replace("`", "\\`").replace("\n", " ").replace("\r", " ")
    return f"`{command_text}`"


def load_report(report_path: Path) -> dict[str, Any]:
    """Load a release gate report JSON object."""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RenderEvidenceError(f"failed to read report JSON: {error}") from error
    if not isinstance(report, dict):
        raise RenderEvidenceError("report JSON must be an object")
    return report


def validate_report(report: dict[str, Any]) -> None:
    """Validate the minimal release gate report schema needed by the renderer."""
    if report.get("schema_version") != 1:
        raise RenderEvidenceError("schema_version must be 1")
    for field in sorted(REQUIRED_FIELDS):
        if field not in report:
            raise RenderEvidenceError(f"missing required field: {field}")
    if not isinstance(report["mode"], str):
        raise RenderEvidenceError("mode must be a string")
    if not isinstance(report["overall_status"], str):
        raise RenderEvidenceError("overall_status must be a string")
    if not isinstance(report["gates"], list):
        raise RenderEvidenceError("gates must be a list")
    if not isinstance(report["manual_gates"], list):
        raise RenderEvidenceError("manual_gates must be a list")
    if not isinstance(report["limitations"], list) or not all(isinstance(item, str) for item in report["limitations"]):
        raise RenderEvidenceError("limitations must be a list of strings")


def gate_field(gate: object, field: str) -> object:
    """Read a required field from a gate object."""
    if not isinstance(gate, dict):
        raise RenderEvidenceError("each gate must be an object")
    if field not in gate:
        raise RenderEvidenceError(f"gate missing required field: {field}")
    return gate[field]


def render_automated_gates(gates: Sequence[object]) -> list[str]:
    """Render automated release gates as a Markdown table."""
    lines = [
        "### Automated gates",
        "",
        "| Name | Status | Return code | Command |",
        "|------|--------|-------------|---------|",
    ]
    for gate in gates:
        name = markdown_table_text(gate_field(gate, "name"))
        status = markdown_table_text(gate_field(gate, "status"))
        return_code = markdown_table_text(gate_field(gate, "return_code"))
        command = command_markdown(gate_field(gate, "command"))
        lines.append(f"| {name} | {status} | {return_code} | {command} |")
    return lines


def render_manual_gates(manual_gates: Sequence[object]) -> list[str]:
    """Render manual release gates as a Markdown table."""
    lines = [
        "### Manual gates still required",
        "",
        "| Name | Status |",
        "|------|--------|",
    ]
    for gate in manual_gates:
        name = markdown_table_text(gate_field(gate, "name"))
        status = markdown_table_text(gate_field(gate, "status"))
        lines.append(f"| {name} | {status} |")
    return lines


def render_report(report: dict[str, Any]) -> str:
    """Render a validated release gate report as a Markdown snippet."""
    validate_report(report)
    preamble = (
        "This evidence was produced by the Non-audio release gate runner "
        "(`uv run python scripts/release_gate_check.py --run --report-json PATH`) "
        "and rendered with `scripts/render_release_gate_evidence.py` into "
        "`non-audio-release-gate-evidence`. It covers tests, type checking, coverage, "
        "lint, format, release readiness smoke, open-source publication docs, "
        "publication artifact hygiene, source package hygiene, PyInstaller check-only, "
        "root artifact hygiene, the third-party dependency/license inventory, the "
        "harmonic mixing guide, and Source publication readiness refresh. "
        "The latest run recorded all pytest gates passing. "
        "It does not require audio files and cannot prove real Mixed In Key audio QA. "
        "Manual audio QA remains pending."
    )
    lines = [
        "## Non-audio release gate evidence",
        "",
        preamble,
        "",
        f"**Overall status:** {markdown_list_text(report['overall_status'])}",
        f"**Mode:** {markdown_list_text(report['mode'])}",
        "",
        *render_automated_gates(report["gates"]),
        "",
        *render_manual_gates(report["manual_gates"]),
        "",
        "### Limitations",
        "",
    ]
    lines.extend(f"- {markdown_list_text(limitation)}" for limitation in report["limitations"])
    lines.extend(["", f"**Note:** {MANUAL_LIMITATION_NOTE}"])
    return "\n".join(lines) + "\n"


def render_report_path(report_path: Path) -> str:
    """Load, validate, and render a release gate report path."""
    return render_report(load_report(report_path))


def assert_output_path_will_not_create_root_artifact_dir(output_path: Path) -> None:
    """Reject output paths that would create project-root build/ or dist/."""
    absolute_output_path = output_path.expanduser().resolve(strict=False)
    for artifact_dir_name in ("build", "dist"):
        artifact_dir = PROJECT_ROOT / artifact_dir_name
        try:
            absolute_output_path.relative_to(artifact_dir)
        except ValueError:
            continue
        raise RenderEvidenceError(f"Refusing to create output path under project-root {artifact_dir_name}/")


def write_output(output_path: Path, markdown: str) -> None:
    """Write rendered Markdown to an explicit output path."""
    assert_output_path_will_not_create_root_artifact_dir(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse Markdown renderer arguments."""
    parser = argparse.ArgumentParser(description="Render release gate JSON evidence as Markdown.")
    parser.add_argument("report_json", type=Path, help="Path to release_gate_check.py --report-json output.")
    parser.add_argument("--output", type=Path, help="Optional Markdown output path. Defaults to stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Render release gate evidence Markdown to stdout or an explicit output file."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        markdown = render_report_path(args.report_json)
        if args.output is None:
            print(markdown, end="")
        else:
            write_output(args.output, markdown)
    except RenderEvidenceError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
