# Tasks
1. [complete] Capture independent synthetic baseline at 1k/10k/50k, including
   copies/publications, lookup comparisons, elapsed replay, timer responsiveness.
   Full 50k baseline intentionally bounded to 128 results; documented explicitly.
2. [complete] Parent released incremental Apply at 16:17 UTC; final integrated
   gate remains required before project completion.
3. [complete] RED pure batch equivalence/immutability tests; GREEN smallest batch
   helper; REFACTOR; VERIFY focused tests. Commit <=400 changed lines.
4. [complete] RED indexed lookup after sort/filter/rebuild/path edits; GREEN
   helper; REFACTOR; VERIFY focused tests. Commit <=400 changed lines.
5. [complete] RED tick batching/progress/terminal flush/context tests; GREEN
   queue, timer, paint and lifecycle integration; REFACTOR; VERIFY focused tests
   and existing completion tests. Two local slices <=400 changed lines each.
6. [complete] Benchmark all requested sizes and record exact method/limitations;
   verify profile/persistence equivalence and responsiveness.
7. [focused complete; integration pending] 262 focused tests, lint, format and
   scoped type check passed; parent runs integrated release_gate_check.py --run.
   Coverage floor remains exclusively in pyproject.toml.
