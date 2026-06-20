# Spec: Prep Copilot shell methods explicit

## Requirement: Prep Copilot methods are explicit MainWindow methods

Given the desktop shell compatibility map
When the Prep Copilot slice is applied
Then `generate_prep_copilot`, `_apply_prep_copilot_item`, and `apply_selected_prep_copilot_variant` are not present in `LEGACY_LAYOUT_METHODS`
And each name is defined directly on `MainWindow`.

## Requirement: Prep Copilot behavior remains delegated

Given existing Prep Copilot UI actions
When the explicit `MainWindow` methods are called
Then they delegate to the same Prep Copilot service behavior as before.

## Requirement: Unrelated grafts stay stable

Given remaining legacy layout methods outside the Prep Copilot group
When the Prep Copilot slice is applied
Then unrelated grafts remain in `LEGACY_LAYOUT_METHODS` for future slices.
