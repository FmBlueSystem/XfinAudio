# Apply Progress

## RED

`uv run pytest tests/test_main_window_shell_compat.py::test_library_shell_methods_are_explicit_main_window_methods -q` failed because `choose_folder` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Added explicit `MainWindow.choose_folder()` and `MainWindow._refresh_idle_action_state()` delegators to `LibraryController`, then removed both names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## Focused verification

`uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py tests/test_visual_integration.py -q` passed: 137 passed.
