"""GitHub Actions safety checks for non-audio release gates."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "non-audio-release-gates.yml"


def workflow_text() -> str:
    """Read the non-audio release gates workflow as text."""
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_non_audio_release_gates_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_workflow_uses_python_311_and_locked_uv_install() -> None:
    text = workflow_text()

    assert 'python-version: "3.11"' in text
    assert "astral-sh/setup-uv@" in text
    assert "uv sync --locked" in text


def test_workflow_runs_release_gate_check_with_json_report() -> None:
    text = workflow_text()

    assert "scripts/release_gate_check.py --run" in text
    assert "--report-json .release-evidence/release-gate-report.json" in text
    default_gate_step = text.split("Run default non-audio release gates", maxsplit=1)[1].split(
        "Render non-audio release gate Markdown evidence", maxsplit=1
    )[0]
    assert "--include-packaging-build" not in default_gate_step


def test_workflow_renders_markdown_evidence_from_json_report() -> None:
    text = workflow_text()

    assert "scripts/render_release_gate_evidence.py" in text
    assert ".release-evidence/release-gate-report.json" in text
    assert "--output .release-evidence/release-gate-evidence.md" in text


def test_workflow_appends_markdown_evidence_to_github_step_summary() -> None:
    text = workflow_text()

    render_step_index = text.index("Render non-audio release gate Markdown evidence")
    summary_step_index = text.index("Append non-audio release gate evidence to step summary")

    assert render_step_index < summary_step_index
    assert 'cat .release-evidence/release-gate-evidence.md >> "$GITHUB_STEP_SUMMARY"' in text


def test_workflow_uploads_json_report_and_markdown_evidence_artifacts() -> None:
    text = workflow_text()

    assert "actions/upload-artifact@" in text
    assert "name: non-audio-release-gate-evidence" in text
    assert ".release-evidence/release-gate-report.json" in text
    assert ".release-evidence/release-gate-evidence.md" in text
    assert "if-no-files-found: error" in text


def test_workflow_does_not_auto_edit_release_evidence_docs_or_root_build_artifacts() -> None:
    text = workflow_text()

    assert "docs/release-candidate-evidence.md" not in text
    assert "path: build" not in text
    assert "path: dist" not in text


def test_workflow_avoids_release_publishing_sensitive_material_and_audio_fixtures() -> None:
    text = workflow_text().lower()

    prohibited_terms = [
        "secrets.",
        "notarytool",
        "stapler",
        "developer_id",
        "codesign",
        "dmg",
        ".mp3",
        ".wav",
        ".aiff",
        ".flac",
        "mixed in key",
        "upload-release-asset",
        "softprops/action-gh-release",
    ]
    for term in prohibited_terms:
        assert term not in text


def test_packaging_build_is_manual_optional_when_present() -> None:
    text = workflow_text()

    if "--include-packaging-build" not in text:
        return

    assert "workflow_dispatch:" in text
    assert "include_packaging_build:" in text
    assert "default: false" in text
    assert "if: ${{ github.event_name == 'workflow_dispatch' && inputs.include_packaging_build }}" in text
