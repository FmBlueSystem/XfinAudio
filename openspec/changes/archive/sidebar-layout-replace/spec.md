# Specification: Replace Tab Sidebar with Proper Navigation

## Requirements

### R1. Sidebar widget

**GIVEN** the app starts  
**WHEN** the main window is shown  
**THEN** a left sidebar lists the 7 navigation items (Library, Build Playlist, Review Mix, Export to Serato, My Playlists, Metadata Worklist, Live Assistant).

### R2. Content area

**GIVEN** the user selects a sidebar item  
**THEN** the corresponding screen fills the area to the right of the sidebar without overlap.

### R3. Active-state highlight

**GIVEN** a sidebar item is selected  
**THEN** it is visually highlighted (color, bold, or background) to indicate the current screen.

### R4. Accessibility

**GIVEN** the sidebar is a QListWidget or QToolBar  
**THEN** each item has an accessible name and supports keyboard navigation.

## Non-functional

- Stay within the 400-line review budget.
- No behavioral change to existing screens.
