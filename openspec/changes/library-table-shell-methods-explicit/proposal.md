# Proposal: Library table shell methods explicit

## Intent

Remove the Library table group from dynamic `shell_layout_compat.LEGACY_LAYOUT_METHODS` grafting by defining explicit `MainWindow` methods that delegate to the existing Library UI services/controllers.

## Scope

In scope:
- `_on_library_selection_changed`
- `show_tracks`
- `set_selected_folder`
- `_persist_last_scan_folder`
- `_populate_track_table`
- `_apply_song_filter`
- `restore_persisted_tracks`
- Regression coverage proving those methods are explicit `MainWindow` methods and absent from the graft map.
- Architecture and elimination-plan documentation updates.

Out of scope:
- Changing library scan, recommendation, export, or metadata behavior.
- Mutating audio files.
- Adding DSP or live Serato DB V2 writes.

## Risk and rollback

Risk is limited to method wiring. Roll back by restoring the graft-map entries and removing the explicit delegators.

## Success criteria

- The seven Library table names are absent from `LEGACY_LAYOUT_METHODS`.
- `MainWindow` exposes explicit callable methods for all seven names.
- Existing focused and full verification gates pass.
- The legacy layout graft map count drops from 28 to 21.
