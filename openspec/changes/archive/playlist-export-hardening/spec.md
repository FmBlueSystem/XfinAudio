# Specification: Playlist & Export Hardening

## Requirements

### R1. Save generated playlist (F1)

**GIVEN** a recommendation exists (`state.last_recommendation is not None`)  
**WHEN** the user clicks "Save to My Playlists" in ReviewScreen  
**THEN** a new playlist is created with the ordered tracks and an auto-generated default name.

**GIVEN** no recommendation exists  
**THEN** the Save button is disabled.

### R2. Rename playlist (F2)

**GIVEN** a playlist is selected in My Playlists  
**WHEN** the user clicks "Rename"  
**THEN** a QInputDialog appears; if the user confirms a non-empty name, the playlist is renamed.

### R3. Export resilience (F3)

**GIVEN** a Serato export is requested without a configured safe folder  
**WHEN** the readiness sidecar write is attempted  
**THEN** the parent directory is created with `mkdir(parents=True, exist_ok=True)`.

**GIVEN** a write still fails (e.g. permission denied)  
**THEN** the user sees a friendly error message instead of an uncaught traceback.

### R4. Real playlist export (F4)

**GIVEN** a saved playlist is loaded in the editor  
**WHEN** the user clicks "Export to Serato" in the editor  
**THEN** the export_coordinator's actual Serato export flow runs against the playlist's tracks.

### R5. Spectral warning aggregation (F5)

**GIVEN** a playlist with N adjacent color shifts  
**THEN** the spectral warnings list contains a single aggregated warning instead of N individual ones.

### R6. Worklist empty state (F7)

**GIVEN** no scanned records exist  
**WHEN** the Metadata Worklist tab is shown  
**THEN** a clear empty-state message is displayed in the table area.

## Non-functional

- The change must not break existing playlist/recommendation/export tests.
- The change must stay within the 400-line review budget.
