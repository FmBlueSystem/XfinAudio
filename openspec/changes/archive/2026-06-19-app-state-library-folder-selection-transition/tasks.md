# Tasks

1. RED: Add a failing transition unit test for immutable library folder selection and scan-dependent reset.
2. GREEN: Implement `apply_library_folder_selected()` and export it.
3. REFACTOR: Wire `LibraryController.set_selected_folder()` through `_replace_state()` while keeping UI/persistence orchestration in the controller.
4. VERIFY: Run focused tests, full gates, and archive the OpenSpec change.
