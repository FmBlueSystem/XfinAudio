# Specification: Visual Hierarchy

## Requirements

### R1. Primary action emphasis

**GIVEN** a screen with a primary action (Scan, Recommend, Export)
**THEN** that button carries `objectName="primaryAction"` and a minimum height larger than the default.

### R2. Secondary action de-emphasis

**GIVEN** a screen with secondary actions (Settings, Cancel, Back, Preview)
**THEN** those buttons carry `objectName="secondaryAction"` and a maximum height smaller than the default.

### R3. Section dividers

**GIVEN** a screen with controls above a table
**THEN** a `QFrame` with `QFrame.Shape.HLine` separates the controls from the table.

### R4. Empty-state illustrations

**GIVEN** the Library screen with no selected folder
**THEN** a "no library" empty-state label is visible.

**GIVEN** the Library screen with a folder but no scanned tracks
**THEN** a "no tracks" empty-state label is visible.

**GIVEN** the Build screen with no recommendation produced
**THEN** a "no recommendation" empty-state label is visible.
