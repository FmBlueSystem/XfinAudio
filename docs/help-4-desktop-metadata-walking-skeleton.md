# HELP-4 Desktop Metadata Walking Skeleton

Date: 2026-06-03

## Scope delivered

HELP-4 adds the first desktop-first metadata slice for XfinAudio:

- PySide6 main window titled `XfinAudio`.
- Folder picker and metadata scan actions.
- Selected folder/status display.
- Tracks table with title, artist, BPM, Camelot key, energy, status, and path.
- Complete/incomplete scan counts.
- Read-only recursive metadata scan service using `mutagen` and the HELP-3 Mixed In Key parser.
- SQLite persistence for scanned track records with schema version `1`.

## Data flow

```text
PySide6 MainWindow -> MetadataScanService -> mutagen read-only tags -> Mixed In Key parser -> TrackRecord -> TrackRepository(SQLite)
```

The UI only wires actions to services/repositories and renders returned records. Metadata parsing, completeness decisions, and persistence are kept outside widgets.

## Persistence

`TrackRepository` stores one row per path and upserts repeat scans. Persisted fields include:

- path
- title
- artist
- bpm
- camelot_key
- energy_level
- genre
- tags JSON
- metadata_status
- missing_required_fields JSON
- source_fields JSON
- raw_metadata JSON

Tests use caller-provided temporary SQLite paths. The desktop launcher uses `~/.xfinaudio/xfinaudio.sqlite3` as the app-controlled database location.

## Safety and non-goals

- No audio files are written or mutated.
- No DSP, C++, audio rendering/mixing, recommendation scoring, playlist strategy, or export behavior is introduced.
- Tests use fake/temp paths and injected metadata readers rather than real user audio files.
- Corrupt or unreadable supported audio files are skipped so one bad file does not abort the folder scan.
