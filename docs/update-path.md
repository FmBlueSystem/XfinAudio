# Update path

XfinAudio stores user data in an app-owned directory that survives package updates. End users can install a newer version with `pip`, `pipx`, or `uv tool` without manual backup or migration steps.

## App-owned paths

| Data | Default path | Purpose |
|------|--------------|---------|
| SQLite database | `~/.xfinaudio/xfinaudio.sqlite3` | Persisted scanned tracks and playlists. |
| Settings JSON | `~/.xfinaudio/settings.json` | User preferences and last scan/safe-export folders. |

These paths are intentionally separate from the Python package installation and from the scanned audio library.

## How updates preserve data

1. **Python package update**
   - Run `pip install --upgrade xfinaudio`, `pipx upgrade xfinaudio`, or `uv tool upgrade xfinaudio`.
   - The package files are replaced; `~/.xfinaudio/` is untouched.
   - On the next launch the app opens the existing database and settings files.

2. **Settings compatibility**
   - `SettingsRepository.load()` returns defaults only when `settings.json` is missing.
   - Existing values are validated by `AppSettings` and preserved.
   - Unknown future settings versions raise a typed `SettingsRepositoryError` so a downgrade or mismatched install fails safely rather than silently resetting preferences.

3. **Database compatibility**
   - `TrackRepository` opens the existing SQLite file and checks `PRAGMA user_version`.
   - New columns are added idempotently with `ALTER TABLE ... ADD COLUMN` when an older database is opened by a newer app version.
   - A database created by a newer unsupported schema version raises `UnsupportedDatabaseVersionError`.

## What users should back up

- Copy `~/.xfinaudio/` before major OS changes or manual SQLite edits.
- The scanned audio files themselves are never modified by XfinAudio, but their paths must remain valid for the persisted library to stay usable.

## Environment overrides

Packaging and smoke tests can redirect data paths without changing user files:

- `XFINAUDIO_DB_PATH` overrides the SQLite database path.
- `XFINAUDIO_SETTINGS_PATH` overrides the settings JSON path.
- `XFINAUDIO_PACKAGE_SMOKE=1` exits before the desktop event loop during packaging validation.

## Unsupported scenarios

- Downgrading to an older app version after the database schema has been advanced is not supported and will raise `UnsupportedDatabaseVersionError`.
- Manual edits to `~/.xfinaudio/xfinaudio.sqlite3` or `~/.xfinaudio/settings.json` can corrupt app state; restore from backup if this happens.
