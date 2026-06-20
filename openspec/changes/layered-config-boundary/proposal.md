# Proposal: Layered config boundary

## Intent
Reduce mixed responsibilities in `xfinaudio.config` by making the settings persistence port explicit while keeping the concrete JSON repository as infrastructure.

## Scope
- Add an explicit `SettingsRepositoryPort` in `xfinaudio.config.ports`.
- Update desktop runtime state typing to depend on the config port rather than a desktop-owned settings persistence protocol.
- Add focused unit tests proving the port is desktop-free and structurally satisfied by `SettingsRepository`.
- Update architecture docs to reflect the improved config boundary.

## Out of Scope
- Changing settings schema or migration behavior.
- Changing settings file format or location.
- DSP, audio mutation, Serato DB V2 writes, export formats, or dependency changes.
- Broad `library`, `exporting`, or `audio` refactors in this first slice.

## Success Criteria
- `xfinaudio.config.ports.SettingsRepositoryPort` exists and imports without desktop/PySide6.
- `SettingsRepository` satisfies the port structurally.
- Desktop app state uses the config port for settings persistence typing.
- Focused and full gates pass.
