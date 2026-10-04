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
