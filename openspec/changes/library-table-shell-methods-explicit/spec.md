# Spec: Library table shell methods explicit

## Requirement: Library table methods are explicit MainWindow methods

Given the desktop shell compatibility map
When the Library table slice is applied
Then `_on_library_selection_changed`, `show_tracks`, `set_selected_folder`, `_persist_last_scan_folder`, `_populate_track_table`, `_apply_song_filter`, and `restore_persisted_tracks` are not present in `LEGACY_LAYOUT_METHODS`
And each name is defined directly on `MainWindow`.

## Requirement: Library table behavior remains delegated

Given existing library UI interactions
When the explicit `MainWindow` methods are called
Then they delegate to the same Library controller/screen services as before.

## Requirement: Unrelated grafts stay stable

Given remaining legacy layout methods outside the Library table group
When the Library table slice is applied
Then unrelated grafts remain in `LEGACY_LAYOUT_METHODS` for future slices.
