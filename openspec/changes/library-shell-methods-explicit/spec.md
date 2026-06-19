# Spec: Library shell methods explicit on MainWindow

## Requirement: Library shell methods are explicit MainWindow methods

`MainWindow` MUST expose the selected Library shell methods as explicit methods rather than receiving them through dynamic legacy layout grafting.

### Scenario: Selected methods stay callable without graft map entries
Given `MainWindow` has been initialized by the desktop shell
When callers access `choose_folder` and `_refresh_idle_action_state`
Then both names must be callable on `MainWindow`
And neither name must appear in `shell_layout_compat.LEGACY_LAYOUT_METHODS`

## Requirement: Remaining legacy layout grafting stays stable

Unrelated legacy layout methods MUST remain installed through the compatibility map during this slice.

### Scenario: Unrelated legacy methods remain grafted
Given existing code expects legacy methods such as `_apply_song_filter`
When `MainWindow` is inspected
Then those methods must remain callable
And their map entries must remain in `LEGACY_LAYOUT_METHODS`
