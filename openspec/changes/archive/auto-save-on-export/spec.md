# Specification: Auto-save Playlist on Export

## Requirements

### R1. Auto-save on successful export

**GIVEN** a recommendation exists and the user triggers a Serato export  
**WHEN** the export completes successfully (crate written, readiness report succeeded)  
**THEN** the current recommendation is persisted as a named playlist in My Playlists.

### R2. No auto-save on preview

**GIVEN** a recommendation exists and the user triggers a preview (not export)  
**WHEN** the preview completes  
**THEN** no playlist is created in My Playlists.

### R3. Idempotency

**GIVEN** a playlist was already auto-saved for the current recommendation  
**WHEN** the user exports again  
**THEN** a new playlist is created (each export = one saved playlist, with a timestamped name).

## Non-functional

- Tests must cover the success and preview-only paths.
- Stay within the 400-line review budget.
