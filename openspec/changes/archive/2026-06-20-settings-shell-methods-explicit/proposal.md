# Proposal: Settings shell methods explicit

## Intent
Reduce desktop shell layout compatibility grafting by moving the Settings shell method group out of `shell_layout_compat.LEGACY_LAYOUT_METHODS` and onto explicit `MainWindow` delegators to `SettingsController`.

## Scope
In scope:
- Make `_open_settings_dialog` and `_on_spectral_cohesion_changed` explicit on `MainWindow`.
- Delegate behavior to `SettingsController`.
- Remove those names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Add focused regression coverage.

Out of scope:
- Changing settings behavior or UI copy.
- Changing scoring/spectral product rules.
- Any audio mutation, DSP, live Serato DB V2 writes, dependency changes, or unrelated graft removals.

## Success Criteria
- Both selected names are absent from `LEGACY_LAYOUT_METHODS`.
- Both selected names are explicit callable methods on `MainWindow`.
- Focused tests and full release gates pass.
- Remaining grafted method count drops from 34 to 32.
