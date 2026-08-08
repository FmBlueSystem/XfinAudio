# AppState Spectral Transition Proposal

## Intent
Remove one real in-place `AppState` mutation from the desktop library controller by extracting a pure transition helper for applying spectral profiles to scanned tracks.

## Scope
In scope:
- Add a UI-independent transition helper for applying a `SpectralProfile` to `AppState.scanned_records` and `AppState.records_by_path`.
- Preserve current UI table update behavior in `LibraryController`.
- Add focused unit tests proving the transition returns a new state and does not mutate the previous state.

Out of scope:
- Global `MainWindow`/`AppController` state sync refactor.
- Scan clearing/refetch lifecycle changes.
- Worker behavior changes.
- Audio mutation, DSP expansion, or Serato behavior.

## Risks
- The list and dict views of a track must remain synchronized.
- Existing UI table update code expects the updated record to be present immediately after the transition.
- Broader state-sync refactors are too coupled for this slice and must remain separate.

## Rollback
Remove the transition helper and restore the previous direct mutation in `LibraryController.on_spectral_profile_ready`.

## Success Criteria
- Focused AppState transition tests pass.
- Spectral progress/main window regression tests still pass.
- Full verification gate passes before claiming completion.
