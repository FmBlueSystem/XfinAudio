# Spec: Layered config boundary

## Requirement: Settings persistence port is explicit

XfinAudio SHALL expose a desktop-free settings persistence port from the config layer.

### Scenario: Settings port imports without UI dependencies

Given a module needs the settings persistence contract,
When it imports `xfinaudio.config.ports.SettingsRepositoryPort`,
Then no `xfinaudio.desktop` or PySide6 dependency SHALL be required.

## Requirement: Concrete settings repository remains compatible

The existing JSON settings repository SHALL satisfy the settings persistence port without changing settings behavior.

### Scenario: Repository loads saved settings through the port

Given a `SettingsRepository` is assigned to `SettingsRepositoryPort`,
When settings are saved and loaded,
Then the loaded value SHALL be an `AppSettings` instance.
