# Apply progress

2026-10-03: proposal, specification, design and tasks written before behavior edits. Branch `feat/electron-ipc-contract`
at `9107b9e`; only the parent-created untracked `odd/tasks/library-boot-recovery.md` was present before this unit.

## RED

Command: `npm --prefix desktop-electron run build` (passed, unchanged source) then
`node --test desktop-electron/tests/renderer.library-boot.test.mjs`.

Observed: 3 tests, 0 pass, 3 fail — markup test missing `#library-recovery`/`#library-retry`; recovery message was
`''`; a double retry started only 1 additional load.

## GREEN

Added the recovery panel markup, `libraryBootError`, `renderLibraryRecovery()`, `bootstrapLibrary()` /
`retryLibraryBootstrap()` and the retry listener. Retry only calls `api.listLibrary()` and returns early while the
gate is busy; success clears the panel and hides the operation status.

Commands: `npm --prefix desktop-electron run build` then
`node --test desktop-electron/tests/renderer.library-boot.test.mjs` — 3 pass, 0 fail.

## TRIANGULATE / regression

`node --test desktop-electron/tests/renderer*.test.mjs desktop-electron/tests/library-host.test.mjs desktop-electron/tests/library-status.test.mjs desktop-electron/tests/errors.test.mjs`
— 205 tests, 205 pass, 0 fail, 0 skipped.

## REFACTOR

None needed: recovery reuses the existing `data-mutation` disable path and adds no timer or new operation kind.

## ODD work unit 2 (bounded first paint)

2026-10-03: implementation stayed inside the renderer surfaces plus these SDD artifacts. Scope was confirmed from
the parent task; the 10,391-row production shape was reproduced as 650 synthetic tracks because the fake-DOM
harness recreates `descendants` by deep traversal on every lookup, which makes 10k pathological rather than revealing.

### RED

Command: `npm --prefix desktop-electron run build` (passed, unchanged source) then
`node --test desktop-electron/tests/renderer.offline-app.test.mjs desktop-electron/tests/renderer.prep.test.mjs`.

Observed: 27 tests, 25 pass, 2 fail — the Library first paint rendered 650 rows instead of 200, and Prep
`prep-start` already held 651 options (650 tracks + "Sin preferencia") right after boot instead of none.

### GREEN

Added `LIBRARY_WINDOW = 200`, the keyed `libraryVisibleLimit` reset, `#library-window` note plus `#library-show-more`,
and lazy `ensureTrackChoices()` population. The Prep controls restore path also calls `ensureTrackChoices()` so a
persisted selection restored before the options existed is reapplied once they are built.

Commands: `npm --prefix desktop-electron run build` (0 errors) then the same focused test command — 27 pass, 0 fail.
Full Electron suite: `node --test desktop-electron/tests/*.test.mjs` — 434 tests, 423 pass, 0 fail, 11 skipped
(pre-existing skips).

### TRIANGULATE / REFACTOR

Search and filter changes reset the window while `library-visible-count` still reports the full match count; three
show-more clicks reach all 650 rows; the deferral test asserts no truncation and preserved selection. Refactor kept a
single window constant and a single revision guard, and reused the existing renderers.
