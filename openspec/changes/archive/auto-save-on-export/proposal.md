# Proposal: Auto-save Playlist on Export

## Intent

When the user exports a recommendation to Serato, automatically persist it as a named playlist in My Playlists so it survives restarts.

## Scope

- In `ExportCoordinator.export_recommendation_to_serato` (or `MainWindow._on_export_recommendation`), after a successful export, call `PlaylistCoordinator.save_recommendation(name=None)` to persist the current recommendation.
- Only auto-save when the export actually succeeded (i.e. the Serato crate was written and the readiness report succeeded).
- Do NOT auto-save when the user previews without exporting.
- Tests covering the success path and the preview-only path.

## Success criteria

1. After a successful Serato export, the playlist appears in My Playlists.
2. After a preview without export, the playlist does NOT appear in My Playlists.
3. All verification commands pass.
4. No audio mutation.
