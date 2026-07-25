"""Guards that Qt is told it is headless before anything imports it.

Twice the CI job burned its full 20-minute timeout inside `uv run pytest` with
ZERO output -- not a progress dot, not a collection error. Both hangs sat on
the same span: `uv sync --locked` had just finished, and the very next line was
the pytest invocation, then silence until the job was cancelled. A stall that
early is import time, not test time; a rerun on a different runner passed the
same suite in 63 seconds.

`conftest.py` was importing PySide6 first and only afterwards announcing the
offscreen platform, and no workflow set it either -- so on a headless macOS
runner Qt came up with no platform hint at all.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_conftest_selects_the_offscreen_platform_before_importing_qt() -> None:
    lines = (PROJECT_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8").splitlines()

    # Comments are skipped: the line explaining this rule names PySide6 too.
    code = [(index, line) for index, line in enumerate(lines) if not line.lstrip().startswith("#")]

    platform_line = next(index for index, line in code if "QT_QPA_PLATFORM" in line)
    first_qt_import = next(index for index, line in code if "PySide6" in line and "import" in line)

    assert platform_line < first_qt_import, "QT_QPA_PLATFORM must be set before PySide6 is imported"


def test_every_workflow_that_runs_tests_declares_the_offscreen_platform() -> None:
    """Belt and braces: conftest only covers what pytest imports.

    A workflow step that reaches Qt outside pytest -- a packaging smoke check,
    a script -- gets no help from conftest.
    """
    workflows = sorted((PROJECT_ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows, "no workflows found"

    offenders = [
        path.name
        for path in workflows
        if "pytest" in (text := path.read_text(encoding="utf-8")) and "QT_QPA_PLATFORM: offscreen" not in text
    ]

    assert offenders == [], f"missing QT_QPA_PLATFORM=offscreen: {offenders}"
