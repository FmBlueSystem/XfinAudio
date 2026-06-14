# Proposal: Reset Settings

## Intent

Allow users to restore all application settings to their release defaults from the Settings dialog, reducing support friction and making the app easier to troubleshoot.

## Scope

### In Scope

- Add a "Reset to Defaults" button to `SettingsDialog`.
- Require confirmation before resetting.
- Emit `settings_changed` with a fresh `AppSettings()` instance when confirmed.
- Add `reset_to_defaults()` convenience method to `SettingsController`.
- Add tests for the controller and dialog.
- Produce SDD/TDD artifacts.

### Out of Scope

- Changing settings schema or default values.
- UI redesign beyond the reset action.
- Translation file updates.

## Capabilities

- `reset-settings`: Users can reset settings to defaults from the Settings dialog.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/settings_dialog.py` | Modified | New reset button and confirmation. |
| `src/xfinaudio/desktop/settings_controller.py` | Modified | New `reset_to_defaults()` method. |
| `tests/test_settings_controller.py` | Created | Controller reset tests. |
| `tests/test_settings_dialog.py` | Created | Dialog reset tests. |
| `openspec/changes/reset-settings/` | Created | SDD/TDD artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Unintended data loss | Low | Confirmation dialog required. |
| Test brittleness | Low | Assert on object name and signal payload, not translated text. |

## Success Criteria

- [ ] Settings dialog has a reset button.
- [ ] Reset requires confirmation.
- [ ] Reset restores `AppSettings()` defaults.
- [ ] Reset persists defaults through the existing repository.
- [ ] All verification commands pass.
