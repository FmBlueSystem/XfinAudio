# Tasks
1. [x] Read governance and audit, isolate branch, complete proposal/spec/design.
2. [x] Parent explicitly authorized isolated Apply after preceding gate completed with integration failures.
3. [x] RED: helper tests for dirty/mismatched source and bundle evidence/integrity.
4. [x] GREEN/REFACTOR: minimal helper; run focused tests and static checks.
5. [x] RED: shell tests for gate failure, reuse refusal, success, changed source.
6. [x] GREEN/REFACTOR: wire exact gate/provenance, preserve optional macOS steps.
7. [x] RED: immutable action references and archive-only download regression.
8. [x] GREEN/REFACTOR: pins and unused-signature cleanup; document integrity scope.
9. [x] VERIFY: focused synthetic suite, shell syntax, type/lint/format checks.
10. [x] Parent VERIFY: full integrated release gate on committed exact HEAD.

Integrated verification completed on 2026-09-30 at `9e7c894`: all automated release gates passed, 2921 tests and 93.54% coverage. Native validation remains separate.
