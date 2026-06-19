# Apply Progress: MainWindow State Compatibility Boundary

## Status
Implementation complete; verification in progress.

## RED
`uv run pytest tests/test_main_window_shell_compat.py::test_shell_compat_exposes_legacy_state_write_boundary -q` failed because `shell_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES` did not exist.

## GREEN
Added `LEGACY_APP_STATE_WRITE_ATTRIBUTES` and `try_set_legacy_app_state_attribute()` to `xfinaudio.desktop.shell_compat`, then delegated `MainWindow.__setattr__` to that helper.

## Refactor
`MainWindow` now uses `shell_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES` as the single source of truth for AppState-backed compatibility attributes, avoiding drift between read and write compatibility.
