# Specification: Undo/Redo

## Requirements

### R1. Undo stack

**GIVEN** a destructive action is performed
**THEN** the action is added to the undo stack

### R2. Undo action

**GIVEN** the undo stack is not empty
**WHEN** the user presses Ctrl+Z
**THEN** the last action is undone

### R3. Redo stack

**GIVEN** an action is undone
**THEN** the action is added to the redo stack

### R4. Redo action

**GIVEN** the redo stack is not empty
**WHEN** the user presses Ctrl+Shift+Z
**THEN** the last undone action is redone

### R5. Undo/redo buttons

**GIVEN** the main window is shown
**THEN** undo/redo buttons are in the toolbar

### R6. Undo history

**GIVEN** the undo stack is not empty
**THEN** undo history is shown in a dropdown
