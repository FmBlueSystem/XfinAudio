# Apply Progress: Export shell methods explicit

Status: verify-pending

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_export_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `choose_safe_export_folder` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow` delegators for the selected Export / Safe Export shell methods.
- Removed the selected Export / Safe Export names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Updated architecture docs to record the slice.

Focused command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_export_shell_methods_are_explicit_main_window_methods -q
```

Result: `1 passed`.
