"""``openspec/config.yaml`` must describe the project this repository is.

The Qt desktop was removed in 4e31a3a together with PySide6, but the SDD
configuration kept describing the tree that no longer exists: it declared
``PySide6``, ``pyobjc-framework-Cocoa`` and ``Python >=3.11``, its dependency
lists had drifted from ``pyproject.toml`` in both directions (``packaging`` and
``pyloudnorm`` were missing, PySide6 was extra), and the UI test layer still
named ``pytest + PySide6 offscreen``. A session that trusts the config
regenerates the wrong environment, so the file is guarded against the real
metadata instead of being trusted.

Like ``tests/test_local_checkout_references.py`` this reads YAML as text:
PyYAML is not a dependency of this project, and indentation is what decides
which section a literal belongs to.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "openspec" / "config.yaml"
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
LOCK_PATH = PROJECT_ROOT / "uv.lock"
# ``Python`` is an interpreter declaration, not a distribution this project
# installs, so it has no lock entry to point at.
INTERPRETER_PREFIX = "python"
DISTRIBUTION_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def config_text() -> str:
    """Read the OpenSpec project configuration as text."""
    return CONFIG_PATH.read_text(encoding="utf-8")


def pyproject() -> dict[str, object]:
    """Load ``pyproject.toml``, the owner of the real dependency metadata."""
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def declared_block(key: str) -> list[str]:
    """Return the non-empty lines nested under the first ``key:`` declaration."""
    lines = config_text().splitlines()
    for index, line in enumerate(lines):
        if line.strip() != f"{key}:" and not line.strip().startswith(f"{key}: "):
            continue
        indent = len(line) - len(line.lstrip(" "))
        block: list[str] = []
        for follower in lines[index + 1 :]:
            if follower.strip() and len(follower) - len(follower.lstrip(" ")) <= indent:
                break
            block.append(follower)
        return block
    return []


def declared_pins(key: str) -> list[str]:
    """Return the ``- name ...`` pins of a list declaration such as ``core_dependencies:``."""
    pins: list[str] = []
    for line in declared_block(key):
        stripped = line.strip()
        if stripped.startswith("- "):
            pins.append(stripped[2:].strip())
    return pins


def distribution_name(requirement: str) -> str:
    """Return the lowercase distribution name of a requirement or pin line."""
    match = DISTRIBUTION_NAME.match(requirement.strip().strip('"'))
    assert match is not None, f"unparseable requirement: {requirement!r}"
    return match.group(1).lower()


def declared_dependency_names(key: str) -> set[str]:
    """Return the distribution names declared in a config dependency list."""
    names = {distribution_name(pin) for pin in declared_pins(key)}
    return {name for name in names if not name.startswith(INTERPRETER_PREFIX)}


def pyproject_requirement_names(requirements: list[str]) -> set[str]:
    """Return the distribution names of ``pyproject.toml`` requirement strings."""
    return {distribution_name(requirement) for requirement in requirements}


def locked_distribution_names() -> set[str]:
    """Return every distribution name resolved in ``uv.lock``."""
    return set(re.findall(r'(?m)^name = "([^"]+)"$', LOCK_PATH.read_text(encoding="utf-8")))


def ruff_settings() -> dict[str, object]:
    """Return ``[tool.ruff]`` from ``pyproject.toml``."""
    return pyproject()["tool"]["ruff"]  # type: ignore[index]


def test_config_exists() -> None:
    assert CONFIG_PATH.exists()


def test_declared_python_floor_matches_pyproject() -> None:
    """``>=3.11`` was declared while ``requires-python`` said ``>=3.12``."""
    declared = next(line for line in declared_block("python") if line.strip().startswith("requires:"))
    declared_requires = declared.split(":", maxsplit=1)[1].strip().strip('"').strip("'")

    assert declared_requires == pyproject()["project"]["requires-python"]  # type: ignore[index]


def test_core_dependencies_match_pyproject_runtime_dependencies() -> None:
    """The runtime list must be the same set of distributions ``pyproject.toml`` installs."""
    expected = pyproject_requirement_names(pyproject()["project"]["dependencies"])  # type: ignore[index]
    declared = declared_dependency_names("core_dependencies")

    assert declared == expected, f"missing: {sorted(expected - declared)}; extra: {sorted(declared - expected)}"


def test_dev_dependencies_match_pyproject_dev_group() -> None:
    """``packaging`` and ``pyloudnorm`` were missing from the declared dev list."""
    expected = pyproject_requirement_names(pyproject()["dependency-groups"]["dev"])  # type: ignore[index]
    declared = declared_dependency_names("dev_dependencies")

    assert declared == expected, f"missing: {sorted(expected - declared)}; extra: {sorted(declared - expected)}"


def test_every_declared_dependency_is_in_the_lockfile() -> None:
    """``PySide6`` and ``pyobjc-framework-Cocoa`` were declared long after they were removed."""
    locked = locked_distribution_names()
    declared = sorted(declared_dependency_names("core_dependencies") | declared_dependency_names("dev_dependencies"))
    unbuildable = [name for name in declared if name not in locked]

    assert unbuildable == [], f"openspec/config.yaml declares distributions absent from uv.lock: {unbuildable}"


def test_ruff_settings_mirror_pyproject() -> None:
    """The config quotes the lint target and line length; both drifted from the owner."""
    declared = {
        line.strip().split(":", maxsplit=1)[0]: line.strip().split(":", maxsplit=1)[1].strip()
        for line in declared_block("ruff")
        if ":" in line and not line.strip().startswith("#")
    }
    settings = ruff_settings()

    assert declared["target_version"] == settings["target-version"]
    assert declared["line_length"] == str(settings["line-length"])


def test_test_layers_do_not_name_the_removed_qt_toolkit() -> None:
    """The UI layer was declared as ``pytest + PySide6 offscreen`` after PySide6 left."""
    offenders = [
        line.strip()
        for line in declared_block("test_layers")
        if any(toolkit in line for toolkit in ("PySide6", "pyobjc", "Qt"))
    ]

    assert offenders == [], f"openspec/config.yaml still declares a Qt test layer: {offenders}"


def test_declared_dependency_absent_from_the_lockfile_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard has to bite: a re-declared PySide6 is exactly the regression it exists for."""
    monkeypatch.setattr(
        sys.modules[__name__],
        "config_text",
        lambda: "stack:\n  core_dependencies:\n    - PySide6 >=6.0,<7.0\n",
    )

    with pytest.raises(AssertionError):
        test_every_declared_dependency_is_in_the_lockfile()


def test_python_floor_drift_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale interpreter floor is the other half of the same defect."""
    original = config_text()
    monkeypatch.setattr(
        sys.modules[__name__],
        "config_text",
        lambda: original.replace('requires: ">=3.12"', 'requires: ">=3.11"'),
    )

    with pytest.raises(AssertionError):
        test_declared_python_floor_matches_pyproject()
