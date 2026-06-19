# Apply Progress

- RED: Added `test_apply_library_records_loaded_replaces_records_and_lookup_immutably`; it failed because `apply_library_records_loaded` did not exist.
- GREEN: Added `apply_library_records_loaded()` to replace loaded records and rebuild `records_by_path` immutably.
- REFACTOR: Updated `LibraryController.populate_track_table()` to render the table, then replace AppState through the pure transition; removed direct `scanned_records` assignment from persisted restore.
- Focused verification passed for the transition, stale folder clearing, last-scan-folder restore, and startup persisted-track restore.
