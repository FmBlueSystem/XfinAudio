# Apply progress
2026-09-30: inspected audit CQ6, repository governance, current transition,
controller, worker-chain and screen-table behavior. Isolated worktree starts at
0f2725e. Planning and baseline only; no production or test change applied.
Parent correctness-tranche gate confirmation is required before RED/Apply.

Parent explicitly released independent Apply at 16:17 UTC while addressing the
correctness-tranche gate failures separately. RED: two pure batch tests failed
for the missing transition (after correcting an invalid loudness test fixture).
GREEN/REFACTOR: one keyed immutable transition, shared replacement records,
ordered-view compatibility, unknown-path handling, progress-only cheap copies.
Focused VERIFY: batch and existing transition tests pass.

RED: indexed-row tests could not import the missing helper. GREEN/REFACTOR:
index live Path items (Qt updates row() during native sorting), invalidate on
structural/Path-cell changes only. VERIFY: sort, hidden rows, rebuild, removal,
Path edits, repeated lookups, and active Color sorting pass without rescanning.


Controller RED: 13 intended assertions failed after selecting a writable test
HOME (the first attempt only exposed the sandbox's read-only default home).
A 1,000-record burst published 3,001 snapshots instead of zero before its tick;
terminal and paint assertions also exposed synchronous result handling.
GREEN/REFACTOR: parent-owned zero-delay single-shot timer, coalesced latest
profiles/progress, bounded per-delivery loudness progress, direct indexed batch
painting with one sort suspension, terminal flushing, and context invalidation.
VERIFY: all new regressions pass; focused Pyright and lint/format are clean.
Parent confirmed the three unrelated broad MainWindow readiness fixture failures
are already corrected on integration commit 6f7a769; their expectations remain
unchanged here. Final aggregate release gate stays with the integration parent.
