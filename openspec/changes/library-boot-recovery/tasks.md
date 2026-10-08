# Tasks

## ODD work unit 1 (recovery)

1. [x] RED: add `tests/renderer.library-boot.test.mjs`; build the unchanged source and record the three failing cases.
2. [x] GREEN: add the recovery panel markup, `libraryBootError` state, `renderLibraryRecovery()`,
   `bootstrapLibrary()`/`retryLibraryBootstrap()` and the retry listener.
3. [x] TRIANGULATE: negative retry-while-busy case and "retry must not scan or choose" assertion; success clears the panel.
4. [x] REFACTOR: keep recovery in its own panel and reuse the existing `data-mutation` disable path; no new timer or
   retry state machine.
5. [ ] VERIFY full gate: `uv run python scripts/release_gate_check.py --run` against the frozen commit is parent-owned.

## ODD work unit 2 (bounded first paint)

1. [x] RED: add bounded-paint tests with 650 synthetic tracks in `tests/renderer.offline-app.test.mjs` and
   `tests/renderer.prep.test.mjs`; build the unchanged source and record the two failing cases.
2. [x] GREEN: slice the Library table to a 200-row window with a keyed reset, add the `#library-window` note and
   `#library-show-more` affordance, and populate Prep selects lazily via `ensureTrackChoices()`.
3. [x] TRIANGULATE: search/metadata identity resets the window while the full match count stays reported; show-more
   reaches all 650 rows; deferred Prep population keeps every track and the selected ID.
4. [x] REFACTOR: keep one window constant and one revision guard; reuse the existing `renderTable` and
   `renderTrackChoices` instead of adding a second list renderer or a truncated option cap.
5. [ ] VERIFY full applicable gate is parent-owned; the focused renderer suite is recorded in `apply-progress.md`.

ODD work unit 3 (sealed QA artifact) remains out of this change.
