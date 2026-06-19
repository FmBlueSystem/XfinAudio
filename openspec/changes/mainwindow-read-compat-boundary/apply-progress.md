# Apply Progress: MainWindow Read Compatibility Boundary

## Status
Implementation complete; verification in progress.

## RED
`uv run pytest tests/test_main_window_shell_compat.py::test_shell_compat_exposes_legacy_state_read_boundary -q` failed because `shell_compat.try_get_legacy_app_state_attribute` did not exist.

## GREEN
Added `try_get_legacy_app_state_attribute()` and `is_missing_legacy_attribute()` to `xfinaudio.desktop.shell_compat`, then delegated `MainWindow.__getattr__` to that helper.

## Refactor
The read helper now owns legacy delegated reads, private attribute protection, AppState alias reads, and scan token synchronization while `MainWindow.__getattr__` remains a thin fallback.
