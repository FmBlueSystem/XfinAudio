# Proposal: AppState playlist removal transition boundary

## Intent
Extract playlist remove/restore state rules from desktop controller mutation into pure AppState transition helpers.

## Problem
`LibraryController` currently mutates `playlist_removed_paths` directly when review tracks are removed or restored. That keeps state-transition policy inside desktop orchestration and makes the UI controller responsible for business state updates.

## Scope
- Add pure helpers for removing and restoring playlist paths in `xfinaudio.desktop.app_state_transitions`.
- Keep `LibraryController` responsible for commands, undo wiring, and UI synchronization only.
- Add focused unit tests before production code changes.

## Out of scope
- No UI redesign.
- No recommendation algorithm changes.
- No export behavior changes.
- No audio mutation, DSP expansion, or Serato DB V2 writes.

## Success criteria
- Playlist removal/restoration state changes are covered by focused unit tests.
- Desktop controller delegates state policy to pure helpers.
- Existing undo/redo behavior remains unchanged.
- Full release gate passes.
