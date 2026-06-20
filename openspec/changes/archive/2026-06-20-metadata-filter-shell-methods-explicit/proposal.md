# Proposal: Metadata filter shell methods explicit

## Intent

Remove the Metadata filter group from dynamic `shell_layout_compat.LEGACY_LAYOUT_METHODS` grafting by defining explicit `MainWindow` methods that delegate to existing metadata/library filtering behavior.

## Scope

In scope:
- `_selected_metadata_status_filter`
- `_selected_missing_metadata_filter`
- `_metadata_status_records`
- `_metadata_missing_field_records`
- Regression coverage proving those methods are explicit `MainWindow` methods and absent from the graft map.
- Architecture and elimination-plan documentation updates.

Out of scope:
- Changing metadata status semantics or filter behavior.
- Changing library scan, recommendation, export, or spectral behavior.
- Mutating audio files.
- Adding DSP or live Serato DB V2 writes.

## Risk and rollback

Risk is limited to method wiring. Roll back by restoring the graft-map entries and removing the explicit delegators.

## Success criteria

- The four Metadata filter names are absent from `LEGACY_LAYOUT_METHODS`.
- `MainWindow` exposes explicit callable methods for all four names.
- Existing focused and full verification gates pass.
- The legacy layout graft map count drops from 21 to 17.
