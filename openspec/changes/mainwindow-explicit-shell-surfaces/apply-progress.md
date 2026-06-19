# Apply Progress

## RED

`uv run pytest tests/test_main_window_shell_compat.py::test_main_window_uses_explicit_shell_compatibility_surfaces -q` failed because `MainWindow` still imported `shell_compat as _shell_compat`.

## GREEN

Updated `MainWindow` to import `shell_layout_compat` and `shell_state_compat` directly. Focused RED test passed.

## Focused verification

`uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py -q` passed: 121 passed.
