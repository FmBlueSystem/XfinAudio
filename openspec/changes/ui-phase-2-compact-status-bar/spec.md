# Specification: Compact Status Bar

## Requirements

### R1. Status bar location

**GIVEN** the main window is shown
**THEN** a status bar is at the bottom of the window (below the workflow tabs)

### R2. Status bar sections

**GIVEN** the status bar is shown
**THEN** it has 3 sections: folder, guidance, scan progress

### R3. Default hidden

**GIVEN** the main window is shown
**THEN** the status bar is hidden by default

### R4. Show during scan

**GIVEN** a scan operation is in progress
**THEN** the status bar is shown automatically
