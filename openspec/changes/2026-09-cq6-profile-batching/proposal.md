# CQ6: batch profile completion publication

## Intent and scope
Reduce cached background-result replay work on the Qt thread without rewriting
AppState, the table model, analysis engines, cache contracts, or persistence.
Batch immutable profile changes at a UI tick; index spectral cell lookup safely
across table sorting, rebuilding, and filtering. Preserve stage order, progress,
visible intermediate results, and completed records.

## Safety, rollback, and success
Synthetic metadata/profiles only; no audio, credentials, live databases, network,
new dependencies, DSP, loudness-policy changes, exports, push, PR, or deployment.
Rollback is the reverse of local conventional commits. Success means equivalent
profile values/order/persistence, bounded collection copies per tick, current
spectral cells before final-stage handoff, and a green integrated release gate.

## Explicit chained delivery plan
Each local conventional commit is <=400 changed lines; no PR is opened.
1. SDD + independent baseline measurements (planning only).
2. RED/GREEN pure batch transition and immutable/equivalence tests.
3. RED/GREEN indexed spectral-row helper and sort/filter/rebuild tests.
4. RED/GREEN controller tick batching and lifecycle/progress tests.
5. Synthetic 1k/10k/50k comparison, verification artifacts and small corrections.
Apply is blocked until parent confirms the current correctness tranche full gate.
