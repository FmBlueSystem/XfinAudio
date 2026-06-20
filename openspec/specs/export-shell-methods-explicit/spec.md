# Spec: Export shell methods explicit on MainWindow

## Requirement: Export shell methods are explicit MainWindow methods

`MainWindow` MUST expose the selected Export / Safe Export shell methods as explicit methods rather than receiving them through dynamic legacy layout grafting.

### Scenario: Selected export methods stay callable without graft map entries
Given `MainWindow` has been initialized by the desktop shell
When callers access the selected Export / Safe Export methods
Then each selected name must be callable on `MainWindow`
And none of those names must appear in `shell_layout_compat.LEGACY_LAYOUT_METHODS`

## Requirement: Export behavior remains delegated to the existing export boundary

The explicit `MainWindow` methods MUST preserve visible export behavior by delegating to the existing export action/coordinator boundary.

### Scenario: Explicit methods delegate instead of owning export logic
Given the selected Export / Safe Export methods are called on `MainWindow`
When each method is invoked with its existing arguments
Then the corresponding existing export action/coordinator behavior must be used
And no export format, safe-folder validation, audio mutation, DSP, or live Serato DB V2 behavior may change

## Requirement: Remaining legacy layout grafting stays stable

Unrelated legacy layout methods MUST remain installed through the compatibility map during this slice.

### Scenario: Unrelated legacy methods remain grafted
Given existing code expects unrelated legacy methods such as `_apply_song_filter`
When `MainWindow` is inspected
Then those methods must remain callable
And their map entries must remain in `LEGACY_LAYOUT_METHODS`
