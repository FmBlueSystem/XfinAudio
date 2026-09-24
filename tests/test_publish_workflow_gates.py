"""GitHub Actions safety checks for the PyPI publication path."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "publish-to-pypi.yml"


def workflow_text() -> str:
    """Read the publish workflow as text."""
    return WORKFLOW_PATH.read_text(encoding="utf-8")


# A block scalar header is `|` or `>` plus an optional chomping (`+`/`-`) and/or
# indentation (1-9) indicator, in either order. Membership in a fixed set of
# plain markers missed `|2` and `|-2`, so the literal marker was recorded as the
# command and the body discarded.
_BLOCK_SCALAR_PATTERN = re.compile(r"^[|>](?:[1-9][+-]?|[+-][1-9]?)?(?:\s+#.*)?$")


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
        if inline and not _BLOCK_SCALAR_PATTERN.fullmatch(inline):
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


@pytest.mark.parametrize(
    "header",
    [
        "|",
        "|-",
        "|+",
        ">",
        ">-",
        ">+",
        "|2",
        "|-2",
        "|+2",
        ">2",
        ">2-",
        ">-2",
        ">+2",
        "|2 # parse with a two-space indent",
    ],
)
def test_run_step_commands_reads_block_scalar_headers(header: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every block scalar header runs the body, not the literal marker.

    A fixed set of plain markers missed headers carrying a chomping or
    indentation indicator such as ``|2`` or ``|-2``; the marker was then recorded
    as the command and the body discarded.
    """
    workflow = (
        "    steps:\n"
        "      - name: demo\n"
        f"        run: {header}\n"
        "          echo one\n"
        "          echo two\n"
        "        shell: bash\n"
    )
    monkeypatch.setattr(sys.modules[__name__], "workflow_text", lambda: workflow)

    assert run_step_commands() == ["echo one", "echo two"]


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


_STEP_NAME_PREFIX = "      - name:"


def step_run_block(step_name: str) -> str:
    """Return the shell body of the workflow step whose name contains step_name."""
    lines = workflow_text().splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(_STEP_NAME_PREFIX) or step_name not in line:
            continue
        run_index = next(
            candidate for candidate in range(index + 1, len(lines)) if lines[candidate].strip().startswith("run:")
        )
        indent = len(lines[run_index]) - len(lines[run_index].lstrip())
        body: list[str] = []
        for continuation in lines[run_index + 1 :]:
            if continuation.strip() and len(continuation) - len(continuation.lstrip()) <= indent:
                break
            body.append(continuation)
        return "\n".join(body)
    raise AssertionError(f"no workflow step named {step_name!r}")


def tag_gate_result(tmp_path: Path, tag: str) -> subprocess.CompletedProcess[str]:
    """Run the real tag/version gate step against a synthetic pyproject in tmp_path."""
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir(exist_ok=True)
    shim = shim_dir / "python"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    shim.chmod(0o755)
    environment = {
        **os.environ,
        "GITHUB_REF_NAME": tag,
        "PATH": f"{shim_dir}{os.pathsep}{os.environ['PATH']}",
    }
    return subprocess.run(
        ["bash", "-c", step_run_block("Require the tag to match the project version")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_tag_gate_reads_the_project_version_with_a_toml_parser(tmp_path: Path) -> None:
    """Regression: `sed | head -1` read the first `version = ` line in the file.

    TOML does not require indentation, so an earlier table may open with its own
    `version = "..."` at column zero and win `head -1`. The empty-value guard
    only noticed "matched nothing"; it never noticed "matched the wrong table".
    A tag naming that nested value passed the gate while the build published
    `[project].version`.
    """
    version = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    (tmp_path / "pyproject.toml").write_text(
        f'[tool.decoy]\nversion = "9.9.9"\n\n[project]\nversion = "{version}"\n',
        encoding="utf-8",
    )

    correct = tag_gate_result(tmp_path, f"v{version}")
    decoy = tag_gate_result(tmp_path, "v9.9.9")

    assert correct.returncode == 0, correct.stdout + correct.stderr
    assert decoy.returncode != 0, f"gate accepted the nested table version: {decoy.stdout}"


def test_publish_workflow_preserves_the_release_gate_evidence() -> None:
    """Regression: a red publish left no record of which gate stopped it.

    The gate step writes `.release-evidence/release-gate-report.json` and the
    job uploaded nothing, so the structured evidence died with the runner the
    moment any gate failed.
    """
    text = workflow_text()

    assert "actions/upload-artifact@" in text, "the publish job uploads no gate evidence"
    assert "- name: Upload release gate evidence" in text
    assert ".release-evidence/release-gate-report.json" in text
    assert "if-no-files-found: error" in text

    upload_step = text[text.index("- name: Upload release gate evidence") : text.index("actions/upload-artifact@")]

    assert "if: always()" in upload_step, "evidence must upload even when a gate fails"


def test_publish_workflow_declares_the_offscreen_qt_platform() -> None:
    """The suite imports Qt while collecting; a headless runner needs the hint."""
    assert "QT_QPA_PLATFORM: offscreen" in workflow_text()
