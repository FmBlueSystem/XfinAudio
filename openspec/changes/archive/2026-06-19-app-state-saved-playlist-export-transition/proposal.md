# Proposal: AppState saved playlist export transition boundary

## Intent
Extract saved-playlist export recommendation replacement from playlist coordinator mutation into a pure AppState transition helper.

## Problem
`PlaylistCoordinator.export_playlist()` directly assigns `host.last_recommendation` when exporting a saved playlist. That keeps AppState recommendation replacement policy inside desktop orchestration.

## Scope
- Add a pure helper for replacing the current recommendation with a saved-playlist export recommendation.
- Keep `PlaylistCoordinator` responsible for repository lookup, editor rendering, and invoking export.
- Add focused unit tests before production changes.

## Out of scope
- No saved playlist repository changes.
- No export writer behavior changes.
- No UI redesign or copy changes.
- No audio mutation, DSP expansion, or Serato DB V2 writes.

## Success criteria
- Saved playlist recommendation replacement is covered by focused tests.
- Playlist coordinator delegates AppState mutation policy to the pure helper.
- Existing saved-playlist export behavior remains unchanged.
- Full release gate passes.
