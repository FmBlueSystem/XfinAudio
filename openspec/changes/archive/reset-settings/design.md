# Design: Reset Settings

## Overview

Add a reset action to the Settings dialog that restores all settings to their release defaults after explicit user confirmation.

## UI flow

```text
SettingsDialog
├── Reset to Defaults button
│   └── clicked → QMessageBox.Yes/No
│       └── Yes → emit settings_changed(AppSettings()) → close dialog
└── OK/Cancel buttons (existing)
```

## Controller flow

```text
SettingsController.reset_to_defaults()
    └── self.apply(AppSettings())
        ├── host.settings = AppSettings()
        ├── settings_repository.save(AppSettings())
        ├── update safe_export_folder_label
        └── _sync_state()
```

## Implementation notes

- The dialog owns the user-facing action and confirmation because it already has the `settings_changed` signal.
- The controller provides `reset_to_defaults()` for clarity and to make testing easier without simulating a button click.
- Default settings are obtained simply by calling `AppSettings()`.

## Tests

- `tests/test_settings_controller.py`: mock `SettingsHost`, call `reset_to_defaults()`, assert host settings are defaults and repository `save()` was called.
- `tests/test_settings_dialog.py`: instantiate `SettingsDialog`, find reset button by object name, click it with confirmation mocked, assert `settings_changed` signal payload equals `AppSettings()`.

## Safety

- Confirmation dialog prevents accidental data loss.
- Reuses existing persistence path; no new schema migrations or file writes.
