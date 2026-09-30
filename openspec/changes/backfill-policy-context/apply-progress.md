# Apply evidence
- Proposal/spec/design/tasks recorded before tests or production edits.
- RED: metadata regression 3 failed (missing policy); direct backfill matrix
  17 failed/2 fallback compatibility passes before production changes.
- Slice 1 GREEN: bounded immutable policy captured at generation filter stages;
  metadata serialization tests and existing behavior suites: 243 passed.
- Slice 1 VERIFY: full Pyright 0 errors; full Ruff lint/format and diff pass.
- Slice 2 RED: expanded direct/desktop matrix 21 failed/12 passed. The desktop
  also rebound an implicit anchor after removal; current lock/exclusion API was
  absent. Enforcement fixed these while preserving the genre fallback tests.
- REFACTOR: tie-order regression caught filter sorting changing equal-score slot
  winners (1 RED failure); shared filters now optionally retain incoming order.
- GREEN/VERIFY: 393 broader focused passes plus 7 export reorder/removal passes;
  full Pyright/Ruff lint/format and diff checks pass. Exact E5/E10 reproduction
  now returns paths a,c with energies 5,5 (no out-of-band replacement).
- No music, Serato, dependency, push, merge or deployment writes.
