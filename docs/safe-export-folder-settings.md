# Safe export folder settings

Date: 2026-06-03

## Scope

XfinAudio persists a user-selected safe export folder in an app-owned JSON settings file. This is settings and UI readiness only: desktop playlist export workflow implementation remains future work.

## Settings path

The desktop default settings path is:

```text
~/.xfinaudio/settings.json
```

The settings repository writes only the caller-provided settings path. It does not use platform-specific settings stores and does not write to audio library folders by default.

## JSON schema behavior

Settings are modeled by `AppSettings` with `settings_version: 1` and an `export` section:

```json
{
  "export": {
    "safe_export_folder": "/path/to/safe/export"
  },
  "optimizer": {
    "exact_limit": 20
  },
  "scan": {
    "supported_extensions": [".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"]
  },
  "scoring": {
    "weights": {
      "bpm": 0.25,
      "energy": 0.25,
      "harmonic": 0.4,
      "tags": 0.1
    }
  },
  "settings_version": 1
}
```

`safe_export_folder` may be `null` when the user has not selected a safe location. Missing settings files load default settings. Future settings versions, malformed JSON, unreadable files, invalid shapes, and write failures raise typed settings repository errors instead of silently downgrading.

Settings JSON is saved with indentation and sorted keys for supportability.

## Safe export folder policy

- XfinAudio never infers the export folder from the scanned audio library folder.
- The desktop UI starts with `No safe export folder selected` when no folder is configured.
- The user can choose a safe export folder and the label updates to show the persisted path.
- The selected safe export folder must not equal the currently selected audio scan folder.
- If the user selects the audio scan folder as the export folder, the UI shows a warning and does not persist the setting.
- No live Serato writes, desktop export buttons, audio mutation, or recommendation behavior changes are part of this implementation.

## Verification

Automated verification on 2026-06-03:

```bash
uv run pytest -v tests/test_settings.py tests/test_settings_repository.py tests/test_main_window.py
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

Results:

```text
21 focused settings/MainWindow tests passed.
136 full-suite tests passed.
Ruff check passed.
49 files already formatted.
```
