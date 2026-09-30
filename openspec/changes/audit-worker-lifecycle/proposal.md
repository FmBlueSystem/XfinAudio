# Safe desktop lifecycle and scan publication

Repair audit CQ-1/CQ-3 and watcher startup recovery without broad architecture changes.
The desktop must remain alive while canceled work settles, retain every worker, and
publish scan completion through its state owner. No audio mutation, DSP additions,
Serato database writes, dependency changes, network requests, push, or deployment.
Risk: slow noninterruptible operations delay closing; show that wait without freezing.
Rollback: revert the affected local commit slice.

## Explicit chained-PR plan

The complete scope exceeds 400 changed lines. Review/apply as dependent slices:
1. `fix: publish scan state and recover watcher startup` (state + watcher + tests)
2. `fix: defer desktop close until workflow threads settle` (shell + service tests)
3. `fix: drain background analysis without terminating threads` (analysis lifecycle + tests)
Each slice targets at most 400 changed lines; split additional test/documentation
slices if necessary. These are local commits only; no PR is opened by this task.
Success: subprocess closes exit normally and preserve committed records; state and
banner clear after success; watcher errors leave scan UI usable with a diagnostic.
