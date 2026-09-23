"""GitHub Actions safety checks for the PyPI publication path."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "publish-to-pypi.yml"


def workflow_text() -> str:
    """Read the publish workflow as text."""
    return WORKFLOW_PATH.read_text(encoding="utf-8")


_BLOCK_SCALARS = {"|", "|-", "|+", ">", ">-", ">+"}


def run_step_commands() -> list[str]:
    """Return the shell commands the workflow actually executes.

    Comments may legitimately mention a command without running it, so this
    reads the `run:` blocks instead of grepping the whole file.
    """
    lines = workflow_text().splitlines()
    commands: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("run:"):
            continue
        inline = stripped.removeprefix("run:").strip()
        if inline and inline not in _BLOCK_SCALARS:
            commands.append(inline)
            continue
        indent = len(line) - len(line.lstrip())
        for continuation in lines[index + 1 :]:
            if not continuation.strip():
                continue
            if len(continuation) - len(continuation.lstrip()) <= indent:
                break
            commands.append(continuation.strip())
    return commands


def test_publish_workflow_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_publish_workflow_runs_the_release_gate_before_publishing() -> None:
    """Regression: the publication path gated almost nothing.

    It ran `uv run pytest -q` and then published: no type check, no lint, no
    coverage floor and none of the hygiene gates the pull-request workflow
    enforces. The path with the least scrutiny shipped to the public index.
    """
    text = workflow_text()

    assert "scripts/release_gate_check.py --run" in text
    assert text.index("scripts/release_gate_check.py --run") < text.index("uv publish")


def test_publish_workflow_does_not_run_the_suite_outside_the_release_gates() -> None:
    """The gate runner already executes the suite; a second step doubles CI time."""
    commands = run_step_commands()
    suite_invocations = [command for command in commands if "pytest" in command]

    assert suite_invocations == [], f"the workflow runs the suite directly: {suite_invocations}"


def test_publish_workflow_requires_the_tag_to_match_the_project_version() -> None:
    """A tag once sat six weeks and 265 commits ahead of the version it published.

    The pull-request workflow refuses a version that did not move. Nothing
    refused a tag that disagreed with `pyproject.toml`, and a tagged build is
    exactly where two files with the same name can hold different builds.
    """
    text = workflow_text()

    assert "GITHUB_REF_NAME" in text
    assert "pyproject.toml" in text
    assert text.index("GITHUB_REF_NAME") < text.index("uv publish")


def test_publish_workflow_declares_the_offscreen_qt_platform() -> None:
    """The suite imports Qt while collecting; a headless runner needs the hint."""
    assert "QT_QPA_PLATFORM: offscreen" in workflow_text()
