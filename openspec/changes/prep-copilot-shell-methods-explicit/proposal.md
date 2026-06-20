# Proposal: Prep Copilot shell methods explicit

## Intent

Remove the Prep Copilot group from dynamic `shell_layout_compat.LEGACY_LAYOUT_METHODS` grafting by defining explicit `MainWindow` methods that delegate to existing Prep Copilot behavior.

## Scope

In scope:
- `generate_prep_copilot`
- `_apply_prep_copilot_item`
- `apply_selected_prep_copilot_variant`
- Regression coverage proving those methods are explicit `MainWindow` methods and absent from the graft map.
- Architecture and elimination-plan documentation updates.

Out of scope:
- Changing Prep Copilot recommendation semantics.
- Changing recommendation/export behavior.
- Mutating audio files.
- Adding DSP or live Serato DB V2 writes.

## Risk and rollback

Risk is limited to method wiring. Roll back by restoring the graft-map entries and removing the explicit delegators.

## Success criteria

- The three Prep Copilot names are absent from `LEGACY_LAYOUT_METHODS`.
- `MainWindow` exposes explicit callable methods for all three names.
- Existing focused and full verification gates pass.
- The legacy layout graft map count drops from 17 to 14.
