# Tasks
1. Complete proposal/spec/design and await integration correctness gate before Apply.
2. RED: demonstrate malformed/unsafe plan rejection, final/backup symlink safety, backup history, atomic publication, failed readback recovery and safe rollback using temporary fixtures.
3. GREEN: implement the smallest safe writer and shared recovery primitives.
4. REFACTOR: retain API compatibility and remove duplicated unsafe I/O.
5. VERIFY: focused crate/application tests, then mandated aggregate release gate; record exact outcomes and limitations.

Integrated verification completed on 2026-09-30 at `9e7c894`: all automated release gates passed, 2921 tests and 93.54% coverage. Native validation remains separate.
