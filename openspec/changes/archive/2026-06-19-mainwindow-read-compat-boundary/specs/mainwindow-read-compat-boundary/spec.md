# MainWindow Read Compatibility Boundary Specification

## ADDED Requirements

### Requirement: Explicit legacy state read compatibility
`MainWindow` MUST delegate legacy AppState-backed attribute reads to an explicit desktop shell compatibility boundary instead of owning the read policy inline.

#### Scenario: AppState-backed read is handled by the compatibility helper
- **GIVEN** a `MainWindow` instance with initialized AppState
- **WHEN** legacy code reads an AppState-backed attribute
- **THEN** the compatibility helper returns the corresponding AppState value without changing visible UI behavior.

### Requirement: Delegated shell reads remain available
`MainWindow` MUST preserve legacy reads for toolbar/controller delegated attributes.

#### Scenario: Delegated toolbar read is handled by compatibility helper
- **GIVEN** a `MainWindow` instance with an undo toolbar
- **WHEN** legacy code reads `undo` or `redo`
- **THEN** the compatibility helper returns the toolbar action.

### Requirement: Missing private attributes stay protected
`MainWindow` MUST continue raising `AttributeError` for unknown private attributes except supported compatibility aliases.

#### Scenario: Unknown private read raises AttributeError
- **GIVEN** a `MainWindow` instance
- **WHEN** code reads an unknown private attribute
- **THEN** `AttributeError` is raised.
