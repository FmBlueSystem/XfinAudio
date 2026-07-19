from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version


def _is_bounded_requirement(constraint: str) -> bool:
    try:
        requirement = Requirement(constraint)
    except InvalidRequirement:
        return False

    for specifier in requirement.specifier:
        if specifier.operator in {"<", "<="}:
            try:
                Version(specifier.version)
            except InvalidVersion:
                continue
            return True
        if specifier.operator == "==" and "*" not in specifier.version:
            try:
                Version(specifier.version)
            except InvalidVersion:
                continue
            return True
    return False


def test_all_direct_dependencies_have_upper_bounds_or_exact_pins() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text())
    constraints = [*config["project"]["dependencies"]]
    constraints.extend(
        constraint for group in config["project"].get("optional-dependencies", {}).values() for constraint in group
    )
    constraints.extend(constraint for group in config.get("dependency-groups", {}).values() for constraint in group)

    unbounded = [constraint for constraint in constraints if not _is_bounded_requirement(constraint)]

    assert unbounded == []


def test_pyobjc_range_supports_python_314_compatible_release() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text())
    pyobjc = next(item for item in config["project"]["dependencies"] if item.startswith("pyobjc-framework-Cocoa"))

    requirement = Requirement(pyobjc)
    assert requirement.specifier.contains("12.2.1")
    assert not requirement.specifier.contains("13.0")


@pytest.mark.parametrize("constraint", ["pkg!=2,<garbage", "pkg===local", "pkg>=1", "pkg==1.*"])
def test_semantic_bound_policy_rejects_malformed_or_non_ordering_constraints(constraint: str) -> None:
    assert not _is_bounded_requirement(constraint)
