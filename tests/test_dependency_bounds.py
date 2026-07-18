from __future__ import annotations

import tomllib
from pathlib import Path


def test_all_direct_dependencies_have_upper_bounds_or_exact_pins() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text())
    constraints = [*config["project"]["dependencies"], *config["dependency-groups"]["dev"]]

    requirements = [constraint.split(";", 1)[0] for constraint in constraints]
    unbounded = [constraint for constraint in requirements if "<" not in constraint and "==" not in constraint]

    assert unbounded == []
