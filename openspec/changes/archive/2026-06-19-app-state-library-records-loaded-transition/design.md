# Design: App State Library Records Loaded Transition

## Approach
Add `apply_library_records_loaded(state, records)` to `desktop.app_state_transitions`. It returns `state.model_copy(update={"scanned_records": list(records), "records_by_path": {record.path: record for record in records}})`.

`LibraryController.populate_track_table()` keeps rendering the UI table, then replaces AppState through the pure transition and `state_setter`. `restore_persisted_tracks()` stops assigning `scanned_records` directly and relies on `populate_track_table()` for the state replacement.

## Safety
No audio files are mutated. No DSP scope is added. No Serato DB V2 writes are introduced.
