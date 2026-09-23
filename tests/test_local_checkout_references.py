"""Live repository files must not point at another local checkout.

A second clone of this repository lived in a different folder for months, and
several operational files pointed at it: the OpenSpec project config, a restart
handoff, and a stray test script. Anything following those pointers worked on a
tree that was hundreds of commits behind, and two separate archived changes had
already recorded the defect without fixing it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "openspec" / "config.yaml"
# Assembled rather than written literally: this file is tracked, and the guard
# below scans tracked files, so a literal path here would make it flag itself.
MACHINE_LOCAL_CHECKOUT = "/".join(("", "Users", "freddymolina", "Documents", "audio"))
# Historical change records and review evidence may cite the old checkout; they
# are the record of what happened, not instructions for what to do next.
HISTORICAL_PREFIXES = ("openspec/changes/", "docs/reviews/")


def config_text() -> str:
    """Read the OpenSpec project configuration as text."""
    return CONFIG_PATH.read_text(encoding="utf-8")


def tracked_files() -> list[str]:
    """Return the repository-relative paths git tracks."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_config_exists() -> None:
    assert CONFIG_PATH.exists()


def test_config_names_no_machine_local_path() -> None:
    """Regression: ``project.root`` named a different, independent checkout."""
    offenders = [line.strip() for line in config_text().splitlines() if "/Users/" in line]

    assert offenders == [], f"machine-local path in openspec/config.yaml: {offenders}"


def test_project_root_is_the_repository_root() -> None:
    """The tooling resolves the project root with ``git rev-parse --show-toplevel``.

    A repository-relative ``.`` is the only value that keeps that meaning in any
    clone, on any machine.
    """
    root_line = next(line for line in config_text().splitlines() if line.strip().startswith("root:"))

    assert root_line.split(":", maxsplit=1)[1].strip().strip('"').strip("'") == "."


def test_declared_source_and_test_roots_exist() -> None:
    for relative in ("src/xfinaudio", "tests"):
        assert f"- {relative}" in config_text(), f"{relative} must stay declared"
        assert (PROJECT_ROOT / relative).is_dir()


def test_referenced_change_paths_exist() -> None:
    """A config pointing at a change nobody can find sends the next session hunting.

    ``current_intent`` referenced a change's design document long after that
    change had been archived under a dated directory.
    """
    missing = [
        reference
        for reference in re.findall(r"openspec/changes/[\w./-]+", config_text())
        if not (PROJECT_ROOT / reference).exists()
    ]

    assert missing == [], f"openspec/config.yaml references missing paths: {missing}"


def test_no_operational_file_points_at_another_local_checkout() -> None:
    """Regression: three live files told the reader to work in a different clone.

    The OpenSpec config named it as the project root, the restart handoff told a
    human to re-open it, and a test script put its ``src`` on ``sys.path``.
    """
    offenders: list[str] = []
    for relative in tracked_files():
        if relative.startswith(HISTORICAL_PREFIXES) or Path(relative).name.startswith("PLAN"):
            continue
        try:
            text = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if MACHINE_LOCAL_CHECKOUT in text:
            offenders.append(relative)

    assert offenders == [], f"live files point at another checkout: {offenders}"
