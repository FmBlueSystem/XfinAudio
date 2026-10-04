# Make the Electron library bootstrap failure visible and retryable

## Intent

The owner's packaged GUI showed an empty Library while the packaged core returned all 10,391 rows from a private
diagnostic copy in ~4.8 s. The exact cause of the empty screen is unproven. Independently, the renderer bootstrap
has a testable defect: when `api.listLibrary()` fails, `perform('library', …)` shows a generic error, `finally`
sets `libraryBootstrapped = true`, and the immediate idle drain (`getLibraryStatus`, preferences) overwrites the
error banner. The table stays empty with no way to retry except restarting the app.

This change keeps the bootstrap failure visibly actionable and adds an explicit, safe reload. It is recovery and
observability, **not** proof that the installed artifact is fixed and not a claim about the 10,391-row render cost.

## Scope

In scope: `desktop-electron/renderer/app.ts`, `index.html`, `styles.css`, synthetic renderer tests, and the SDD
artifacts for this change.

Out of scope: the core/engine, the scanner, audio or profile data, bounded first paint for large libraries
(ODD work unit 2), any packaged artifact (ODD work unit 3), dependencies, and visual redesign.

## Risks and rollback

- Risk: idle work still runs after a failed bootstrap and may change the transient banner. Mitigated by rendering
  recovery in its own panel, so idle work cannot hide the failure.
- Risk: a retry could be mistaken for a rescan. Mitigated by reloading only `listLibrary()`; no folder chooser,
  no rescan, no profile write.
- Rollback: revert the recovery panel plus `bootstrapLibrary`/`retryLibraryBootstrap`; the prior bootstrap line is
  the only removed behavior.

## Success criteria

- A failed bootstrap leaves a visible, actionable message after idle work settles.
- The retry control reloads the library through `listLibrary()` only and is a no-op while the gate is busy.
- A successful (re)load still hides the operation status and clears the recovery panel.

## Budget

One reviewable unit. Expected well under the 400-line review budget including these seven artifacts.
