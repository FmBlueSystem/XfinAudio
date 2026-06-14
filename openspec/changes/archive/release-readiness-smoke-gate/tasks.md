# Tasks: Release Readiness Smoke Gate

## Task 1 — Harden the smoke script

- [ ] Add DJ readiness report step to `scripts/smoke_release_readiness.py`.
- [ ] Keep deterministic `TrackRecord` fixtures and temp SQLite database.
- [ ] Ensure stdout prints a concise pass checklist.
- [ ] Ensure non-zero exit on failure.

## Task 2 — Wire the smoke into the release gate runner

- [ ] Add `release readiness smoke` command gate to `scripts/release_gate_check.py`.
- [ ] Place it after format and before publication-hygiene gates.

## Task 3 — Update tests

- [ ] Update `tests/test_release_gate_check.py` to expect the new gate.
- [ ] Update `tests/test_release_smoke.py` to assert the DJ readiness pass line.

## Task 4 — Document the runbook

- [ ] Create `docs/release-readiness-smoke.md` with commands, expected pass lines, and limitations.

## Task 5 — Verify

- [ ] Run focused tests.
- [ ] Run full pytest suite.
- [ ] Run pyright, coverage, ruff check/format.
- [ ] Run `scripts/release_gate_check.py --run`.
