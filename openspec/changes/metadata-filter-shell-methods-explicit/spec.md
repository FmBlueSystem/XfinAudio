# Spec: Metadata filter shell methods explicit

## Requirement: Metadata filter methods are explicit MainWindow methods

Given the desktop shell compatibility map
When the Metadata filter slice is applied
Then `_selected_metadata_status_filter`, `_selected_missing_metadata_filter`, `_metadata_status_records`, and `_metadata_missing_field_records` are not present in `LEGACY_LAYOUT_METHODS`
And each name is defined directly on `MainWindow`.

## Requirement: Metadata filter behavior remains delegated

Given existing metadata filter UI state
When the explicit `MainWindow` methods are called
Then they delegate to the same metadata/library filtering behavior as before.

## Requirement: Unrelated grafts stay stable

Given remaining legacy layout methods outside the Metadata filter group
When the Metadata filter slice is applied
Then unrelated grafts remain in `LEGACY_LAYOUT_METHODS` for future slices.
