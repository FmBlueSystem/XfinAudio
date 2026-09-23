# Tasks: harden-release-gates

Strict TDD: RED observed before every production change. WU1–WU6 are one commit each.

## WU1 — the publication gate reads the index (B1) — `f89d082`

- [x] 1.1 RED: a test that fails because the gate walks the working tree
- [x] 1.2 GREEN: rewrite the hygiene tests onto the tracked tree
- [x] 1.3 Pin the oracle in both directions inside a throwaway repository
- [x] 1.4 Verify that a git-ignored `.DS_Store` at the repository root no longer fails the suite

## WU2 — one owner for the coverage floor (B4) — `ceb2dc2`

- [x] 2.1 RED: a test refusing `--cov-fail-under` in the gate command
- [x] 2.2 GREEN: remove the flag from the gate command
- [x] 2.3 RED: a test refusing a configured floor far below measured coverage
- [x] 2.4 GREEN: raise `fail_under` to 89

## WU3 — the sdist excludes scratch (B5) — `6302c3e`

- [x] 3.1 RED: a test that an archive carrying `PLAN*.md` or `docs/reviews/**` is refused
- [x] 3.2 GREEN: add `FORBIDDEN_PATH_PREFIXES` and `FORBIDDEN_PATH_PATTERNS` to the inspection
- [x] 3.3 RED: a test that the build configuration excludes the scratch before it is built
- [x] 3.4 GREEN: add the five `[tool.hatch.build.targets.sdist]` exclusions

## WU4 — the publication path is gated (B2) — `837db53`

- [x] 4.1 RED: tests that the workflow runs the release gate, does not run the suite separately, and asserts the tag
- [x] 4.2 GREEN: rewrite the workflow steps
- [x] 4.3 Keep the version step readable, failing with both values named

## WU5 — one repository (E1) — `234d6f5`

- [x] 5.1 RED: a test refusing a tracked file that names another local checkout
- [x] 5.2 GREEN: `project.root` becomes `.`; declared roots and referenced change paths must exist
- [x] 5.3 GREEN: mark the restart handoff as a historical record; delete the dead script
- [x] 5.4 Exempt the historical record, and confirm the guard does not flag its own source

## WU6 — documentation defers to the owner — `39fbeb5`

- [x] 6.1 RED: a test refusing a coverage floor flag in the documented verification sequence
- [x] 6.2 GREEN: `pytest --cov -q`, and the section names `pyproject.toml`
- [x] 6.3 Drive both directions: a reintroduced flag fails, a removed pointer fails

## WU7 — artifacts

- [x] 7.1 proposal, two capability deltas, spec index, design, tasks
- [x] 7.2 apply progress with the work-unit evidence and its provenance
- [x] 7.3 verify report against the local gates
- [x] 7.4 state.yaml

## WU8 — the final gate over the finished tree

- [x] 8.1 `uv run pytest -q`
- [x] 8.2 `uv run pytest --cov -q` against the 89 floor
- [x] 8.3 `uv run pyright src tests`
- [x] 8.4 `uv run ruff check .` and `uv run ruff format --check .`
- [x] 8.5 `uv run python scripts/release_gate_check.py --run`
