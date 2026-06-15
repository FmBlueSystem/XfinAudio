# Specification: Consolidate Tracks Table Ownership

## Requirements

### R1. Single source of truth

**GIVEN** the app starts  
**THEN** `MainWindow` does not create a `tracks_table` attribute.

**GIVEN** a scan completes or spectral profiles update  
**WHEN** the library track list needs to update  
**THEN** `LibraryScreen.tracks_table` is the only table being mutated.

### R2. Behavior preservation

**GIVEN** a user scans, filters, sorts, or removes tracks  
**THEN** the visible Library tab behavior is identical to the previous implementation.

## Non-functional

- The change must not break existing library or main window tests.
- The change must stay within the 400-line review budget.
