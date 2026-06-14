# Apply Progress: Reset Settings

## Summary

All planned tasks were applied. The Settings dialog now includes a "Reset to Defaults" button that restores all settings to their release defaults after confirmation. The SettingsController exposes a reusable `reset_to_defaults()` method.

## Key decisions

- Placed the reset button in the same button row as OK/Cancel, aligned to the left.
- Used `QMessageBox.question` for confirmation to prevent accidental resets.
- Reused the existing `apply()` path for persistence and UI refresh.
- Added object name `reset_to_defaults_button` to the button for stable test selection.

## Files changed

- `src/xfinaudio/desktop/settings_dialog.py`
- `src/xfinaudio/desktop/settings_controller.py`
- `tests/test_settings_controller.py`
- `tests/test_settings_dialog.py`
