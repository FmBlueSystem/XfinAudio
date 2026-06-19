# Specification: MainWindow Read Compatibility Boundary

## Requirement: Explicit legacy state read compatibility
`MainWindow` MUST delegate legacy AppState-backed attribute reads to an explicit desktop shell compatibility boundary instead of owning the read policy inline.

### Scenario: AppState-backed read is handled by the compatibility helper
Given a `MainWindow` instance with initialized AppState
When legacy code reads an AppState-backed attribute
Then the compatibility helper returns the corresponding AppState value without changing visible UI behavior.

## Requirement: Delegated shell reads remain available
`MainWindow` MUST preserve legacy reads for toolbar/controller delegated attributes.

### Scenario: Delegated toolbar read is handled by compatibility helper
Given a `MainWindow` instance with an undo toolbar
When legacy code reads `undo` or `redo`
Then the compatibility helper returns the toolbar action.

## Requirement: Missing private attributes stay protected
`MainWindow` MUST continue raising `AttributeError` for unknown private attributes except supported compatibility aliases.

### Scenario: Unknown private read raises AttributeError
Given a `MainWindow` instance
When code reads an unknown private attribute
Then `AttributeError` is raised.
