# Design

The bootstrap call is extracted from module init into `bootstrapLibrary()`. Its `perform` failure callback stores
`libraryBootError = userErrorMessage(error)`; the success callback clears it, applies the library and hides the
operation status. `renderLibraryRecovery()` writes only `hidden` and `textContent`, so it cannot inject markup.

Recovery is its own panel (`#library-recovery`) inside the library page rather than a second use of the transient
`#operation-status` banner. The generic idle drain keeps overwriting the transient banner, but the recovery panel
is independent, so the failure stays visible and actionable. The retry button is `data-mutation`, so the existing
`syncControls()` disables it whenever the gate is busy or the core is unavailable.

`retryLibraryBootstrap()` returns early when `!coreAvailable || gate.busy`, and `perform` additionally refuses a
second token; retry is therefore idempotent while busy. Retry calls only `api.listLibrary()` — no `chooseLibrary`,
no `rescanLibrary`, no profile write — and does not clear `libraryBootError` before the attempt, so a failed retry
keeps the failure visible.

Affected files: `renderer/app.ts` (state, recovery render, bootstrap/retry, wiring), `renderer/index.html`
(panel markup), `renderer/styles.css` (panel layout), `tests/renderer.library-boot.test.mjs`.

Safety: read-only renderer change. No audio mutation, no DSP, no Serato V2 write, no dependency change.

Testing: deterministic fake-DOM app test through the existing `.out/renderer/app.js` import pattern. The test
proves scheduling/state, not native visibility, geometry or a real Electron launch.
