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

## Bounded first paint (ODD work unit 2)

`renderLibrary` slices the filtered/sorted match array to `LIBRARY_WINDOW = 200` rows before `renderTable`, so the
initial DOM stays bounded instead of synchronously building all 10k+ rows. A `libraryWindowKey` derived from the
search text, metadata filter, AI filter revision, library revision, browsed-set revision and offline sort identity
resets the window whenever the visible identity changes; the inline "show more" handler grows the window without
changing that key, so an explicit load-more is not reset by its own render.

`library-visible-count` and the metadata worklist keep using the full match array, never the slice. `#library-window`
hosts the distinct "showing X of Y" note and the `#library-show-more` button; both hide when the window already
covers every match.

Prep selects are populated lazily through `ensureTrackChoices()`, guarded by `libraryRevision`. `applyLibrary` marks
the library revision and only populates immediately when the Prep page is already active; `navigate('prep')`, the Prep
submit path and the persisted-controls restore call it. `renderTrackChoices` is unchanged in what it offers, so no
track is silently truncated and selected IDs (including dirty "No disponible" ones) are preserved.

Affected files: `renderer/app.ts` (window state, render slice, load-more, lazy choices), `renderer/index.html`
(`#library-window` note/button), `renderer/styles.css` (window layout), `tests/renderer.offline-app.test.mjs` and
`tests/renderer.prep.test.mjs`.

Safety: read-only renderer change. No audio mutation, no DSP, no Serato V2 write, no dependency change.
