# Tasks

1. [x] Recover the staged migration and original RED transcript before changing code.
2. [x] RED old-snapshot/publication/unknown-field mutation tests (4 failures); GREEN replacement publication; REFACTOR narrow current-state access.
3. [x] RED frozen-field tests; GREEN freeze + replace and convert production writers/fixtures; REFACTOR helpers; VERIFY focused state/scan/desktop tests.
4. [x] Add accessor publication and targeted negative/positive type-check regression tests; check all source/tests with Pyright and repository-wide lint/format.
5. [ ] Run the final integrated release gate after all audit slices. The integration owner runs this once on the combined branch; isolated aggregate attempts are not completion evidence.
