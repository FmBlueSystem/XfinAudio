# Tasks
1. RED: reproduce public hard-filter bypass, removed/reordered anchor drift,
   custom loudness band, documented fallbacks, legacy context and lock exceptions.
2. GREEN: capture bounded policy and enforce it in the pure helper/desktop seam.
3. REFACTOR: share existing predicates; keep immutable output and score behavior.
4. VERIFY: focused suites, full Pyright/Ruff/format, diff checks; integration
   owner runs the final combined aggregate gate (not duplicated in this worktree).

Integrated verification completed on 2026-09-30 at `9e7c894`: all automated release gates passed, 2921 tests and 93.54% coverage. Native validation remains separate.
