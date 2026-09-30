# Tasks
1. [in progress] Capture independent synthetic baseline at 1k/10k/50k, including
   copies/publications, lookup comparisons, elapsed replay, timer responsiveness.
2. [pending gate] Parent confirms correctness tranche full release gate.
3. [pending] RED pure batch equivalence/immutability tests; GREEN smallest batch
   helper; REFACTOR; VERIFY focused tests. Commit <=400 changed lines.
4. [pending] RED indexed lookup after sort/filter/rebuild/path edits; GREEN helper;
   REFACTOR; VERIFY focused tests. Commit <=400 changed lines.
5. [pending] RED tick batching/progress/terminal flush/context tests; GREEN queue,
   timer, paint and lifecycle integration; REFACTOR; VERIFY focused tests and
   existing completion tests. Commit slices <=400 changed lines.
6. [pending] Benchmark all requested sizes and record exact method/limitations;
   verify profile/persistence equivalence and responsiveness.
7. [pending] Focused tests, lint, format, type gate, then parent runs integrated
   release_gate_check.py --run (coverage floor exclusively pyproject.toml).
