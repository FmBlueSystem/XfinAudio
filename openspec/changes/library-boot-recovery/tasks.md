# Tasks — ODD work unit 1 only

1. [x] RED: add `tests/renderer.library-boot.test.mjs`; build the unchanged source and record the three failing cases.
2. [x] GREEN: add the recovery panel markup, `libraryBootError` state, `renderLibraryRecovery()`,
   `bootstrapLibrary()`/`retryLibraryBootstrap()` and the retry listener.
3. [x] TRIANGULATE: negative retry-while-busy case and "retry must not scan or choose" assertion; success clears the panel.
4. [x] REFACTOR: keep recovery in its own panel and reuse the existing `data-mutation` disable path; no new timer or
   retry state machine.
5. [ ] VERIFY full gate: `uv run python scripts/release_gate_check.py --run` against the frozen commit is parent-owned.
6. [ ] ODD work units 2 (bounded first paint for 10,391 rows) and 3 (sealed QA artifact) are out of this change.
