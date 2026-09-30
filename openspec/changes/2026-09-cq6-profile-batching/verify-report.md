# Verify report
Pending. Required evidence: immutable/equivalent records, one publication per
tick, bounded progress, terminal flush, row correctness after UI changes,
persisted-profile compatibility, synthetic 1k/10k/50k timings and timer delay.
Final integrated release gate is owned by parent; no completion claim yet.

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
