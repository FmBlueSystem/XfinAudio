# Verify report
Focused verification complete; final integrated release gate is owned by the
parent and remains pending. No release, push, or deployment is authorized here.

## Independent pre-change baseline (0f2725e)
Synthetic actual LibraryController spectral callbacks with a real offscreen
QTableWidget; 128 results delivered per scheduled event-loop chunk and a 1 ms
heartbeat. Table setup is excluded. No audio/engine/repository operation runs.

| Library rows | Cached deliveries | Replay seconds | Publications | Max heartbeat gap |
| --- | --- | --- | --- | --- |
| 1,000 | 1,000 (full) | 0.674265 | 1,000 | 0.311460 s |
| 10,000 | 10,000 (full) | 87.692637 | 10,000 | 7.917307 s |
| 50,000 | 128 (partial, uniformly spread paths) | 10.048740 | 128 | 10.043215 s |

All expected cells and profiles matched, and original immutable records stayed
unchanged. Sync requests equaled publications. Code-path collection-copy count:
two per publication. Exact full-pass row-comparison counts are N(N+1)/2 from the
ordered unique paths. These counts are derived from the inspected loop, not an
instrumented Qt counter. Full 50k baseline was intentionally stopped to avoid
quadratic compute waste and gate contention; no extrapolation is a measured
result. Full post-fix 50k replay remains required.

Pre-change focused baseline: 89 tests passed (state transitions, controller,
library screen; 8.89 seconds). Wall time reflects one synthetic environment and
is informational; deterministic operation-count tests will guard complexity.


## Post-change measurements and reproducibility
The same original replay harness measured full replays at 1k/10k/50k in
0.062254 / 0.339364 / 6.480025 seconds, with maximum heartbeat gaps of
0.012961 / 0.043170 / 0.281878 seconds. All equivalence assertions passed.

The checked-in `scripts/benchmark_profile_replay.py` reproduces the same workload
and additionally instruments collection identities and Path-column item reads.
Run with a writable temporary HOME, `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=src`,
and the project Python environment. Default sizes are 1000, 10000 and 50000;
`--max-results 128` supports the bounded pre-change 50k workload.

| Rows/results | Replay seconds | Publications | Collection replacements | Path reads | Max heartbeat gap |
| --- | --- | --- | --- | --- | --- |
| 1,000 / 1,000 | 0.025535 | 8 | 16 | 1,000 | 0.006531 s |
| 10,000 / 10,000 | 0.344098 | 79 | 158 | 10,000 | 0.035316 s |
| 50,000 / 50,000 | 5.610673 | 391 | 782 | 50,000 | 0.187069 s |

These are single synthetic offscreen runs, not a production latency guarantee.
Table construction is excluded; initial index creation is included. Timings
vary under shared-host load; deterministic counters are the regression signal.
Each tick still walks/copies the library once, so total work depends on tick
count; this does not claim an unconditional linear full-replay algorithm.
Full 50k before/after speedup is not available because baseline was partial.
No audio, engine analysis, user database, or network operation runs in the
benchmark. Its publication callback counts snapshots instead of rendering all
application screens, so it isolates the audited callback/replay cost.

## Requirement evidence
- R1: pure batch tests compare all four profile families to existing single
  transitions; both views share replacements, ordering and original snapshots
  stay intact, unknown paths are omitted, changed records are copied once.
- R2: 1,000-record mixed burst publishes once after a tick, including coalesced
  spectral progress/latest values. Duplicate loudness deliveries still count
  before clamping. Progress-only ticks reuse both collections and preserve
  intervening unrelated state changes.
- R3: spectral and selected-track loudness displays update on the tick; all
  stage completions/cancellations and ordinary shutdown flush before handoff.
  Replacement discards pending UI work. Destruction after Qt timer teardown
  discards unpaintable pending UI work without an exception; this fallback is
  separate from normal shutdown and does not affect already persisted results.
- R4: indexed lookup survives native sorting, hidden rows, row removal, rebuilds
  and Path edits. Repeated lookups/Color sorts do not rescan; batch painting
  disables/restores active native sorting once per batch.
- R5: 151 existing completion-worker and repository regressions exercise cache
  versioning, saved profiles, stage ordering and cancellation; no production
  persistence/engine code changed. Loudness's synchronous test now explicitly
  waits for the batch tick before asserting the published profile.

## Verification result
262 focused tests passed in 15.37 seconds across controller, row index, batch
transitions, library screen, state transitions, targeted MainWindow progress,
all four completion stages and track repository. Scoped Pyright over all changed
production modules/tests: zero errors/warnings. Ruff check/format passed for all
changed Python files; diff whitespace check passed.

An earlier broader MainWindow run had 231 passed and 3 unrelated readiness
fixture failures. Parent confirmed those expectations are repaired on integrated
commit `6f7a769`; this branch deliberately leaves them unchanged. No aggregate
gate was run concurrently here; parent owns final full-suite/coverage/release
gate on the integrated commit. Platform/manual real-audio QA remains separate.
