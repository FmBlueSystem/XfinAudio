# Proposal: Playlist & Export Hardening

## Intent

Address audit findings F1, F2, F3, F4, F5, and F7 from the Fagan Inspection: make generated playlists saveable, make export resilient to missing directories, wire the playlist export properly, and clean up noisy warnings and empty states.

## Scope

### In scope

- F1: Add "Save to My Playlists" action in ReviewScreen.
- F2: Add QInputDialog for rename in MyPlaylistsScreen.
- F3: mkdir parents before writing readiness sidecars; catch OSError in export handler.
- F4: PlaylistCoordinator.export_playlist delegates to the real export flow.
- F5: Aggregate adjacent same-color spectral warnings into one summary.
- F7: Add explicit empty state for Metadata Worklist when no records.

### Out of scope

- F6 (dual tracks_table) — separate refactor PR.

## Success criteria

1. User can save a generated playlist with a custom name from ReviewScreen.
2. User can rename a saved playlist via a dialog.
3. Export does not crash when safe folder is missing; friendly error shown.
4. Exporting a saved playlist from My Playlists triggers a real Serato export.
5. Review tab shows one aggregated spectral warning instead of N per-color warnings.
6. Metadata Worklist shows clear empty state when no library is scanned.
7. All verification commands pass.
8. No audio files are mutated.

## Rollback plan

- Revert the changes; features are opt-in or behind existing flows.

## Review budget

Estimated changed lines: ~150 production + ~80 test lines, within the 400-line budget.
