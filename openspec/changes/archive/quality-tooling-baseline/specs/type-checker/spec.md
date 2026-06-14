# Spec: Static Type Checking with pyright

## Goal

Enable static type checking for the XfinAudio Python codebase using `pyright`.

## Acceptance Criteria

- `pyright` is declared as a dev dependency in `pyproject.toml`.
- `pyproject.toml` contains a `[tool.pyright]` section configured for Python 3.11.
- `uv run pyright src tests` completes without unhandled type errors or with explicit suppressions.
- `openspec/config.yaml` records `type_checker.available: true` and the command to run it.
- The CI workflow runs pyright as part of the non-audio release gates.

## Configuration

- `typeCheckingMode`: "basic" to start.
- `include`: `["src", "tests"]`.
- `exclude`: `[".venv", "build", "dist", "node_modules"]`.
- `pythonVersion`: "3.11".
- `reportMissingTypeStubs`: false (many dependencies lack stubs).
- `reportUnknownParameterType` and `reportUnknownVariableType`: false initially to avoid noise.

## Behavior Changes

None. This is a tooling-only change.
