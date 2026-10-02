# Tasks
1. RED: test recorded exclusions, current exclusions, genre, explicit anchor,
   locked/manual exceptions and explicit anchor removal with synthetic records.
2. GREEN: retain controls metadata and reuse it at the replacement boundary.
3. REFACTOR: check policy is shared rather than duplicated.
4. VERIFY: focused regression tests, lint/type checks, integrated release gate.

Integrated verification completed on 2026-09-30 at `9e7c894`: all automated release gates passed, 2921 tests and 93.54% coverage. Native validation remains separate.
