# Specification: Keyboard Shortcuts

## Requirements

### R1. Focus search

**GIVEN** the Library screen is shown
**WHEN** the user presses Ctrl+F
**THEN** the search input is focused

### R2. Start scan

**GIVEN** the Library screen is shown and a folder is selected
**WHEN** the user presses Ctrl+Shift+S
**THEN** the scan starts

### R3. Recommend playlist

**GIVEN** the Build Playlist screen is shown and tracks are selected
**WHEN** the user presses Ctrl+R
**THEN** the recommendation starts

### R4. Export to Serato

**GIVEN** the Export screen is shown and a recommendation exists
**WHEN** the user presses Ctrl+E
**THEN** the export starts

### R5. Toggle Missing column

**GIVEN** the Library screen is shown
**WHEN** the user presses Ctrl+M
**THEN** the Missing column is toggled

### R6. Preview track

**GIVEN** a track is selected in the Library
**WHEN** the user presses Space
**THEN** the track preview starts/stops (already exists)

### R7. Open track

**GIVEN** a track is selected in the Library
**WHEN** the user presses Enter
**THEN** the track opens in the default player

### R8. Remove track

**GIVEN** a track is selected in a playlist
**WHEN** the user presses Delete
**THEN** the track is removed from the playlist
