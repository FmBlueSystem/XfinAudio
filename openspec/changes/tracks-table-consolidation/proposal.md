# Proposal: Consolidate Tracks Table Ownership

## Intent

Remove the dead `MainWindow.tracks_table` and migrate all code to operate on the visible `LibraryScreen.tracks_table`, eliminating the dual-table maintenance hazard.

## Scope

### In scope

- Remove `self.tracks_table` from `MainWindow._build_widgets`.
- Migrate `MainWindow._populate_track_table` to populate `self._library_screen.tracks_table`.
- Migrate `MainWindow._on_spectral_profile_ready` to update `self._library_screen.tracks_table`.
- Migrate `MainWindow._apply_song_filter` and sort handlers to use the LibraryScreen table.
- Update tests to assert the visible table is populated.

### Out of scope

- Behavioral changes to the Library screen.
- Column additions or removals.

## Success criteria

1. `MainWindow` no longer creates its own `tracks_table`.
2. All track-list operations target `self._library_screen.tracks_table`.
3. All existing library tests pass.
4. All verification commands pass.
5. No audio files are mutated.

## Rollback plan

- Re-add `self.tracks_table` to `MainWindow` and revert the migrations.

## Review budget

Estimated changed lines: ~80 production + ~20 test lines, within the 400-line budget.
