# Proposal: AppState track constraints transition boundary

## Intent
Extract excluded/locked track constraint state updates from desktop controller mutation into pure AppState transition helpers.

## Problem
`LibraryController` currently mutates `excluded_paths` and `locked_paths` directly when users exclude, lock, or clear constraints. That keeps state-transition policy inside desktop orchestration.

## Scope
- Add pure helpers for excluding, locking, and clearing track constraints.
- Keep `LibraryController` responsible for reading selection and syncing UI only.
- Add focused unit tests before production changes.

## Out of scope
- No recommendation algorithm changes.
- No UI redesign or copy changes.
- No audio mutation, DSP expansion, or Serato DB V2 writes.

## Success criteria
- Constraint state updates are covered by focused unit tests.
- Desktop controller delegates AppState transition policy to pure helpers.
- Existing UI behavior remains unchanged.
- Full release gate passes.
