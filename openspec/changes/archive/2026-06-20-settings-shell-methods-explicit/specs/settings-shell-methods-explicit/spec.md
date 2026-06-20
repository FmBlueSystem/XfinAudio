# Spec: Settings shell methods explicit on MainWindow

## Requirement: Settings shell methods are explicit MainWindow methods

`MainWindow` MUST expose the selected Settings shell methods as explicit methods rather than receiving them through dynamic legacy layout grafting.

### Scenario: Settings methods stay callable without graft map entries
Given `MainWindow` has been initialized by the desktop shell
When callers access `_open_settings_dialog` and `_on_spectral_cohesion_changed`
Then both names must be callable on `MainWindow`
And neither name must appear in `shell_layout_compat.LEGACY_LAYOUT_METHODS`

## Requirement: Settings behavior remains delegated

The explicit `MainWindow` methods MUST preserve visible settings behavior by delegating to `SettingsController`.

### Scenario: Explicit methods delegate to SettingsController
Given the selected Settings shell methods are called on `MainWindow`
When `_open_settings_dialog` or `_on_spectral_cohesion_changed` is invoked
Then the corresponding `SettingsController` behavior must be used
And no settings product behavior may change

## Requirement: Remaining legacy layout grafting stays stable

Unrelated legacy layout methods MUST remain installed through the compatibility map during this slice.

### Scenario: Unrelated legacy methods remain grafted
Given existing code expects unrelated legacy methods such as `_apply_song_filter`
When `MainWindow` is inspected
Then those methods must remain callable
And their map entries must remain in `LEGACY_LAYOUT_METHODS`
