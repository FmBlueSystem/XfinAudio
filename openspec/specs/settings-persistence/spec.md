# Spec: Settings Persistence (Audio Preview Extension)

## Capability

`settings-persistence`

## Intent

Extend the existing app settings to store and restore the audio preview volume level across app sessions.

## Current State

`AppSettings` (via `src/xfinaudio/config/settings.py`) persists:
- `safe_export_folder: str`
- `last_scan_folder: str`
- `ui.language: str`

Settings are stored in a JSON file managed by `SettingsRepository`.

## Changes

### New Field: preview_volume

Add a new field to `AppSettings`:

```python
preview_volume: float = Field(default=0.7, ge=0.0, le=1.0)
```

- Default value: `0.7` (70% volume).
- Validation: must be between `0.0` and `1.0` inclusive.
- Pydantic handles missing field gracefully on load (uses default).

### Settings Dialog Extension

Optionally add a volume slider to the Settings dialog:
- Label: "Preview Volume" / "Volumen de previsualización"
- Slider: 0-100 mapped to 0.0-1.0
- Value persisted immediately or on dialog accept.

## Acceptance Criteria

### AC-1: Default volume

Given a fresh install with no existing settings
When the app starts
Then the preview volume is `0.7`.

### AC-2: Volume persistence

Given the user sets the preview volume to `0.3`
When the app is restarted
Then the preview volume is restored to `0.3`.

### AC-3: Volume applied to player

Given the app starts with a stored volume of `0.5`
When the AudioPlayer is initialized
Then its volume is set to `0.5`.

### AC-4: Backward compatibility

Given an existing `settings.json` without `preview_volume`
When settings are loaded
Then the default value `0.7` is used
And the settings file is valid.

## Constraints

- Must use the existing Pydantic settings model.
- Must not break existing settings tests.
- Must follow strict TDD.
