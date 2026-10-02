# Apply progress

2026-10-02: Hosted run 36949151681 is a successful workflow with incomplete Python execution, not an all-tests-pass result. Raw artifacts are retained with hashes. Source/proposal initialized before regressions and implementation. No previous gate or host outcome is rewritten.

2026-10-02 RED: Real disposable pytest projects with setup skips and call skips both returned success from the unmodified batch guard. The legacy-job FFmpeg prerequisite regression also failed: 3 failed, 1 passed. Production files remained unchanged until these failures were captured.

2026-10-02 GREEN: Mirrored the existing public Homebrew FFmpeg install/probe into the legacy job before its aggregate. The batch plugin now records only non-skipped call reports; setup alone cannot satisfy the manifest. Successful and failed call evidence retain their existing exit statuses and identities. Four new parametrized test cases were added; workflow permissions, action pins, limits, dependency versions, coverage floor and application code were not changed by this slice.

2026-10-02 VERIFY: 52 focused tests passed, then 61 tests passed including action-pin and aggregate-sharding contracts. Targeted Pyright reported 0 errors/warnings and Ruff 0.15.15 lint/format passed. Code/test delta is 51 additions and 1 deletion across four files. Full aggregate and fresh hosted verification remain pending coordination.
