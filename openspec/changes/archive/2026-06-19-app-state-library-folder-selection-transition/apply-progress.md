# Apply Progress

- RED: Added `test_apply_library_folder_selected_sets_folder_and_resets_scan_context_immutably`; it failed because `apply_library_folder_selected` did not exist.
- GREEN: Added `apply_library_folder_selected()` by composing `apply_scan_context_reset()` and replacing `selected_folder` immutably.
- REFACTOR: Updated `LibraryController.set_selected_folder()` to use the pure transition and split scan-dependent UI clearing into `_clear_scan_dependent_ui()`.
- Focused verification passed for the transition, folder shortcut, and folder-change stale-state behavior.
