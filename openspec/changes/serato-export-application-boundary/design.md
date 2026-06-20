# Serato Export Application Boundary Design

Add `xfinaudio.application.serato_playlist_export`:
- `preview_serato_playlist_export(...)` selects the library and builds the crate plan.
- `export_serato_playlist(...)` previews, then writes with explicit `confirm=True`.
- Writer and discoverer dependencies are injectable for tests and desktop adapter seams.

`ExportCoordinator` passes its discoverer seam into the use case so existing desktop/main-window tests can still control Serato library selection.
