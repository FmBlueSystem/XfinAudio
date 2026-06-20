# Design: Layered config boundary

## Approach
Create `xfinaudio.config.ports.SettingsRepositoryPort` as a protocol for settings persistence. Replace the desktop-owned `SettingsPersistence` protocol in `desktop.app_state` with an alias to this config port so the contract belongs to the layer that owns settings concepts.

## Affected Files
- `src/xfinaudio/config/ports.py`
- `src/xfinaudio/desktop/app_state.py`
- `tests/test_settings_ports.py`
- `docs/architecture/layered-architecture.md`

## Safety
No runtime settings schema, storage path, export, audio, DSP, Serato, or dependency behavior changes.
