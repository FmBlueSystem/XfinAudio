# Proposal: Scan entry shell methods explicit

## Intent
Reduce desktop shell layout compatibility grafting by moving the Scan entry method group out of `shell_layout_compat.LEGACY_LAYOUT_METHODS` and onto explicit `MainWindow` delegators to existing scan/library owners.

## Scope
In scope:
- Make `scan_selected_folder`, `_begin_scan_state`, `cancel_scan`, and `_clear_scan_dependent_state` explicit on `MainWindow`.
- Delegate behavior to `ScanService` or `LibraryController`.
- Remove those names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Add focused regression coverage.
- Update architecture docs and the compatibility elimination tracker.

Out of scope:
- Changing scan behavior, worker lifecycle, cancellation semantics, or UI copy.
- Moving library table, metadata, recommendation, prep-copilot, or spectral methods.
- Audio mutation, DSP expansion, live Serato DB V2 writes, dependency changes.

## Success Criteria
- The four selected names are absent from `LEGACY_LAYOUT_METHODS`.
- The four selected names are explicit callable methods on `MainWindow`.
- Focused tests and full release gates pass.
- Remaining grafted method count drops from 32 to 28.
