# Avoid redundant local-search scoring

The covered integrated 50-track performance fixture intermittently exceeded its existing two-second limit. Isolated measurements showed no justification for relaxing that limit: the original path took 114–152 ms and the corrected path 120–159 ms; the latter took 846–1,002 ms with coverage.

Profiling found 14,762 score calls for 7,381 candidate paths because the unchanged incumbent was rescored for each candidate. Cache its score once per local-search pass without changing the objective, candidate enumeration, ties, or returned order.

This is an isolated review slice below 400 changed lines. It adds no dependency, DSP work, or audio/Serato writes. Rollback is the isolated commit. Success means the operation-count regression and existing optimizer/performance tests pass without relaxed thresholds.
