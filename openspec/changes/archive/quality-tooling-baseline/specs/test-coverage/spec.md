# Spec: Test Coverage Measurement with pytest-cov

## Goal

Measure and enforce a baseline test coverage threshold for the XfinAudio test suite using `pytest-cov`.

## Acceptance Criteria

- `pytest-cov` is declared as a dev dependency in `pyproject.toml`.
- `pyproject.toml` contains a `[tool.coverage.run]` section with `source = ["src"]` and `branch = false`.
- `uv run pytest --cov --cov-fail-under=70` passes against the current test suite.
- `openspec/config.yaml` records `coverage.available: true` and the command to run it.
- The CI workflow runs coverage as part of the non-audio release gates.

## Configuration

- `branch = false` to keep the initial baseline simple.
- `fail-under = 70` as a minimum threshold; raise in future changes.
- `omit` patterns for `__main__`, build scripts, and smoke harnesses if needed.

## Behavior Changes

None. This is a tooling-only change.
