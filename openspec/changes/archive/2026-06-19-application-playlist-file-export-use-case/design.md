# Design: Application Playlist File Export Use Case

## Approach
Create `xfinaudio.application.playlist_file_export` with a small use case API:

- `PlaylistFileExportWriters`: writer dependency bundle for Rekordbox, Traktor, and VirtualDJ.
- `PlaylistFileExportResult`: plan plus written path.
- `preview_playlist_file_export(...)`: returns a `PlaylistFileExportPlan` without writing.
- `export_playlist_file(...)`: builds the plan, dispatches to the selected writer, and returns the result.

`desktop.export_coordinator` will keep UI gate handling, selected software, labels, and exception rendering. For non-Serato exports it will call the application use case rather than dispatching writer functions directly.

## Affected Files
- `src/xfinaudio/application/playlist_file_export.py`
- `src/xfinaudio/desktop/export_coordinator.py`
- `tests/test_application_playlist_file_export.py`
- Existing export coordinator tests for regression coverage.

## Safety
No audio mutation, no DSP expansion, no live Serato DB V2 writes. Serato export remains out of scope.
