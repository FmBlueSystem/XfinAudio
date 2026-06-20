# Apply Progress: Settings shell methods explicit

Status: verify-pending

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_settings_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `_open_settings_dialog` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow._open_settings_dialog()` delegating to `SettingsController.open_settings_dialog()`.
- Added explicit `MainWindow._on_spectral_cohesion_changed()` delegating to `SettingsController.on_spectral_cohesion_changed()`.
- Removed the two Settings names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Updated architecture docs and elimination plan progress.

Focused command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_settings_shell_methods_are_explicit_main_window_methods -q
```

Result: `1 passed`.
