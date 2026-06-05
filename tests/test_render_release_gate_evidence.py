"""Markdown renderer tests for release gate JSON evidence."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "render_release_gate_evidence.py"

_render_spec = importlib.util.spec_from_file_location("render_release_gate_evidence", RENDER_SCRIPT_PATH)
assert _render_spec is not None
assert _render_spec.loader is not None
render_release_gate_evidence = importlib.util.module_from_spec(_render_spec)
_render_spec.loader.exec_module(render_release_gate_evidence)


def sample_report() -> dict[str, object]:
    """Build a minimal valid release gate report."""
    return {
        "schema_version": 1,
        "mode": "check-only",
        "gates": [
            {
                "name": "tests",
                "status": "listed",
                "return_code": None,
                "command": ["uv", "run", "pytest", "-q"],
            },
            {
                "name": "source package hygiene",
                "status": "listed",
                "return_code": None,
                "command": ["uv", "run", "python", "scripts/source_package_hygiene_check.py"],
            },
            {
                "name": "root artifact hygiene",
                "status": "listed",
                "return_code": None,
                "command": [],
            },
        ],
        "manual_gates": [
            {"name": "real Mixed In Key audio QA", "status": "pending_manual"},
            {"name": "clean macOS account validation", "status": "pending_manual"},
            {"name": "signing/notarization/DMG", "status": "pending_manual"},
        ],
        "overall_status": "listed",
        "limitations": [
            "Does not prove real Mixed In Key audio QA",
            "Does not prove clean macOS account validation",
            "Does not prove signing, notarization, DMG distribution, or release completion",
        ],
    }


def write_report(path: Path, report: dict[str, object] | None = None) -> None:
    """Write a JSON report fixture."""
    path.write_text(json.dumps(sample_report() if report is None else report), encoding="utf-8")


def test_valid_report_renders_expected_markdown_tables_and_limitations(tmp_path: Path) -> None:
    report_path = tmp_path / "release-gate-report.json"
    write_report(report_path)

    markdown = render_release_gate_evidence.render_report_path(report_path)

    assert "## Non-audio release gate evidence" in markdown
    assert "**Overall status:** listed" in markdown
    assert "**Mode:** check-only" in markdown
    assert "| Name | Status | Return code | Command |" in markdown
    assert "| tests | listed | — | `uv run pytest -q` |" in markdown
    assert (
        "| source package hygiene | listed | — | `uv run python scripts/source_package_hygiene_check.py` |" in markdown
    )
    assert "| root artifact hygiene | listed | — | — |" in markdown
    assert "| Name | Status |" in markdown
    assert "| real Mixed In Key audio QA | pending_manual |" in markdown
    assert "- Does not prove real Mixed In Key audio QA" in markdown
    assert (
        "does not prove manual audio QA, clean macOS account validation, "
        "signing/notarization/DMG, or release completion" in markdown
    )
    assert "release is complete" not in markdown


def test_main_writes_markdown_to_stdout_by_default(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    report_path = tmp_path / "release-gate-report.json"
    write_report(report_path)

    assert render_release_gate_evidence.main([str(report_path)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "## Non-audio release gate evidence" in captured.out
    assert "| tests | listed | — | `uv run pytest -q` |" in captured.out


def test_output_writes_file_and_creates_parent_directory(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    report_path = tmp_path / "release-gate-report.json"
    output_path = tmp_path / "nested" / "evidence.md"
    write_report(report_path)

    assert render_release_gate_evidence.main([str(report_path), "--output", str(output_path)]) == 0

    assert capsys.readouterr().out == ""
    assert output_path.read_text(encoding="utf-8").startswith("## Non-audio release gate evidence")


def test_invalid_schema_fails_nonzero_and_does_not_write_output(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    report_path = tmp_path / "release-gate-report.json"
    output_path = tmp_path / "evidence.md"
    report = sample_report()
    report["schema_version"] = 2
    write_report(report_path, report)

    assert render_release_gate_evidence.main([str(report_path), "--output", str(output_path)]) == 1

    captured = capsys.readouterr()
    assert "schema_version must be 1" in captured.err
    assert captured.out == ""
    assert not output_path.exists()


def test_missing_required_field_fails_nonzero_and_does_not_write_output(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    report_path = tmp_path / "release-gate-report.json"
    output_path = tmp_path / "evidence.md"
    report = sample_report()
    del report["manual_gates"]
    write_report(report_path, report)

    assert render_release_gate_evidence.main([str(report_path), "--output", str(output_path)]) == 1

    captured = capsys.readouterr()
    assert "missing required field: manual_gates" in captured.err
    assert captured.out == ""
    assert not output_path.exists()


def test_malformed_json_fails_nonzero_and_does_not_write_output(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    report_path = tmp_path / "release-gate-report.json"
    output_path = tmp_path / "evidence.md"
    report_path.write_text("{not-json", encoding="utf-8")

    assert render_release_gate_evidence.main([str(report_path), "--output", str(output_path)]) == 1

    captured = capsys.readouterr()
    assert "failed to read report JSON" in captured.err
    assert captured.out == ""
    assert not output_path.exists()


def test_output_refuses_project_root_build_or_dist_paths(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(render_release_gate_evidence, "PROJECT_ROOT", tmp_path)
    report_path = tmp_path / "release-gate-report.json"
    write_report(report_path)

    for artifact_dir_name in ("build", "dist"):
        output_path = tmp_path / artifact_dir_name / "evidence.md"

        assert render_release_gate_evidence.main([str(report_path), "--output", str(output_path)]) == 1

        captured = capsys.readouterr()
        assert f"Refusing to create output path under project-root {artifact_dir_name}/" in captured.err
        assert captured.out == ""
        assert not output_path.exists()

    assert not (tmp_path / "build").exists()
    assert not (tmp_path / "dist").exists()
