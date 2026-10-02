# Immutable desktop state contracts
Close CQ7 incrementally: prevent field mutation/unknown update keys, convert remaining production mutations to published replacement snapshots, and add targeted typed current-state/replacement contracts. Preserve existing public rendering/workflow behavior and legacy shell property callers; no giant widget/model rewrite.
Risks: stale snapshots if any shell/service update is not published; constructor wiring order; tests that mutate fixtures must use supported replacement. Rollback individual local commits. No audio/DSP/export semantics changes.
## Chained review plan
1. Explicit state update/publication behavior and accessor regression tests.
2. Frozen AppState fields, checked model_copy and immutable helpers; convert direct writes and fixture setup.
3. Narrow type-check contract tests and final integration evidence.
Combined >400 lines permitted only as this explicit chain; target each production slice <=400 changed lines. No publication authorized.
