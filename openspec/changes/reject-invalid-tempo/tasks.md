# Tasks
1. RED: Add synthetic parser, beatgrid fallback, symmetric score/helper and readiness regressions; capture failures.
2. GREEN: Add shared validation and defensive guards.
3. REFACTOR: Keep one validity contract and existing candidate precedence.
4. VERIFY: Run focused targets, lint, format and type checks; integration lead owns final exact-commit release gate.

Integrated verification completed on 2026-09-30 at `9e7c894`: all automated release gates passed, 2921 tests and 93.54% coverage. Native validation remains separate.
