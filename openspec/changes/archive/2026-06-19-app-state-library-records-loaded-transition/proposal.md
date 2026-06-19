# Proposal: App State Library Records Loaded Transition

## Intent
Move library record loading/indexing policy out of `LibraryController` direct mutation into a pure AppState transition.

## Scope
- Add a pure transition that stores loaded/scanned records and rebuilds `records_by_path` immutably.
- Update `LibraryController.populate_track_table()` and persisted-library restore flow to use the transition.
- Preserve table rendering, filtering, labels, guidance copy, and spectral worker orchestration in the controller.

## Out of Scope
- Changing metadata parsing, scanning workers, recommendation logic, Serato export, or audio files.
- Refactoring legacy `layout.py` compatibility functions in this slice.

## Success Criteria
- Loaded records and lookup map are updated together via a pure transition.
- `LibraryController` no longer directly mutates `scanned_records` or `records_by_path` for table population/restoration.
- Focused and full verification gates pass.
