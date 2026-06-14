# Tasks: Compatibility Matrix

## Task 1 — Create matrix doc

- [ ] Create `docs/serato-compatibility-matrix.md`.
- [ ] Include version rows, fixture validation status, and known limitations.

## Task 2 — Cross-reference

- [ ] Update `docs/serato-fixture-compatibility.md` to link to the matrix.

## Task 3 — Add test

- [ ] Create `tests/test_serato_compatibility_matrix.py` asserting the doc content.

## Task 4 — Verify

- [ ] Run focused and full pytest suites.
- [ ] Run pyright, coverage, ruff check/format.
- [ ] Run `scripts/release_gate_check.py --run`.
