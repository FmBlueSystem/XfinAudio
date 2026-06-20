# Proposal: Export shell methods explicit

## Intent
Reduce desktop shell layout compatibility grafting by moving the Export / Safe Export method group out of `shell_layout_compat.LEGACY_LAYOUT_METHODS` and onto explicit `MainWindow` delegators.

## Scope
In scope:
- Make selected Export / Safe Export shell methods explicit on `MainWindow`.
- Delegate behavior to the existing export action/coordinator boundary.
- Remove the selected names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Add regression coverage proving the methods stay callable without dynamic layout grafting.
- Update architecture documentation and verification artifacts.

Out of scope:
- Changing export formats or safe export rules.
- Mutating audio files.
- Adding DSP, live Serato DB V2 writes, or dependency changes.
- Reworking unrelated scan, recommendation, metadata, spectral, or prep-copilot grafted methods.

## Methods
- `choose_safe_export_folder`
- `set_safe_export_folder`
- `_format_safe_export_folder_label`
- `export_dj_readiness_report`
- `preview_export`
- `export_recommendation`
- `preview_serato_export`
- `export_recommendation_to_serato`
- `export_metadata_status_to_serato`

## Risks
- Screens and menus still call these methods on `MainWindow`; explicit methods must preserve callability.
- Export safety behavior must remain delegated to the existing export action/coordinator path.

## Rollback
Restore the method names to `shell_layout_compat.LEGACY_LAYOUT_METHODS` and remove the explicit delegators/tests from this slice.

## Success Criteria
- Selected Export / Safe Export names are absent from `LEGACY_LAYOUT_METHODS`.
- Selected names are callable on `MainWindow` as explicit class methods.
- Focused shell compatibility tests pass.
- Full verification gates pass before completion.
- Review budget remains below 400 changed lines.
