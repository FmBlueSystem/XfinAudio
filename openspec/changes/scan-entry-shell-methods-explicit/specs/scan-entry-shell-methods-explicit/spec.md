# Spec: Scan entry shell methods explicit on MainWindow

## Requirement: Scan entry shell methods are explicit MainWindow methods

`MainWindow` MUST expose the selected Scan entry shell methods as explicit methods rather than receiving them through dynamic legacy layout grafting.

### Scenario: Scan entry methods stay callable without graft map entries
Given `MainWindow` has been initialized by the desktop shell
When callers access `scan_selected_folder`, `_begin_scan_state`, `cancel_scan`, and `_clear_scan_dependent_state`
Then each name must be callable on `MainWindow`
And none of those names must appear in `shell_layout_compat.LEGACY_LAYOUT_METHODS`

## Requirement: Scan behavior remains delegated

The explicit `MainWindow` methods MUST preserve visible scan behavior by delegating to the existing scan/library owners.

### Scenario: Explicit scan methods delegate to existing owners
Given the selected Scan entry shell methods are called on `MainWindow`
When each method is invoked
Then scan lifecycle behavior must continue to use `ScanService`
And scan-dependent UI cleanup must continue to use `LibraryController`
And no scan worker, cancellation, audio, DSP, or persistence semantics may change

## Requirement: Remaining legacy layout grafting stays stable

Unrelated legacy layout methods MUST remain installed through the compatibility map during this slice.

### Scenario: Unrelated legacy methods remain grafted
Given existing code expects unrelated legacy methods such as `_apply_song_filter`
When `MainWindow` is inspected
Then those methods must remain callable
And their map entries must remain in `LEGACY_LAYOUT_METHODS`
