# Spec: Drop Node toolchain

## ADDED Requirements

### Requirement: No Node toolchain files may be tracked

The repository root MUST NOT contain a `package.json` or `pnpm-lock.yaml` file. The
repository MUST NOT have any tracked file under `node_modules/`. Local untracked
artifacts (e.g. `.opencode/node_modules/`) are out of scope.

#### Scenario: Root has no Node manifest

- **WHEN** `git ls-files package.json pnpm-lock.yaml` is invoked
- **THEN** it returns no entries.

#### Scenario: No tracked node_modules

- **WHEN** `git ls-files node_modules` is invoked
- **THEN** it returns no entries.

### Requirement: Local Node artifacts must be removed

The local `node_modules/` directory at the repository root MUST be removed.

#### Scenario: No local node_modules at the root

- **WHEN** `ls -d node_modules` is invoked at the repo root
- **THEN** it returns "No such file or directory".

### Requirement: .gitignore must continue to ignore Node artifacts

The `.gitignore` MUST continue to list `node_modules/`, `package.json`, and
`pnpm-lock.yaml` so a future inadvertent `pnpm install` does not re-track them.

#### Scenario: .gitignore still covers Node

- **WHEN** `.gitignore` is read
- **THEN** it contains lines for `node_modules/`, `package.json`, and `pnpm-lock.yaml`.

## MODIFIED Requirements

None.

## REMOVED Requirements

None.

## Invariants

- `pyproject.toml`, `uv.lock`, and the Python source tree MUST remain intact.
- `.opencode/` (opencode plugin runtime) MUST remain intact and is out of scope.
- `scripts/release_gate_check.py` and `scripts/source_package_hygiene_check.py`
  MUST NOT reference Node artifacts.
