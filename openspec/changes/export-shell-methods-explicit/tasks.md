# Tasks: Export shell methods explicit

- [x] RED: Add regression coverage proving selected Export / Safe Export names are explicit `MainWindow` methods and absent from `LEGACY_LAYOUT_METHODS`.
- [x] GREEN: Add explicit `MainWindow` delegators for selected Export / Safe Export methods.
- [x] GREEN: Remove selected Export / Safe Export names from `shell_layout_compat.LEGACY_LAYOUT_METHODS` while preserving unrelated grafts.
- [x] VERIFY: Run focused shell compatibility tests and full release gates.
- [x] DOCS: Update architecture docs, apply progress, verify report, and state.
