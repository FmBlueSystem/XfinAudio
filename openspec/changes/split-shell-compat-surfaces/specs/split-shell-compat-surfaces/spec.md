# Split Shell Compatibility Surfaces Specification

## ADDED Requirements

### Requirement: Layout compatibility has its own surface
Legacy layout method grafting MUST live in a layout-specific compatibility module.

#### Scenario: Layout compatibility module owns method installation
- **GIVEN** the desktop shell compatibility code
- **WHEN** legacy layout methods are installed on `MainWindow`
- **THEN** the layout compatibility module owns the method map and installation behavior.

### Requirement: AppState compatibility has its own surface
Legacy MainWindow AppState read/write compatibility MUST live in a state-specific compatibility module.

#### Scenario: State compatibility module owns AppState reads and writes
- **GIVEN** legacy code reads or writes AppState-backed attributes
- **WHEN** `MainWindow` delegates the compatibility operation
- **THEN** the state compatibility module handles it without changing visible behavior.

### Requirement: Shell facade remains stable
Existing imports from `desktop.shell_compat` MUST remain valid while callers migrate to narrower modules.

#### Scenario: Existing facade exports continue to work
- **GIVEN** existing tests import `desktop.shell_compat`
- **WHEN** they access legacy compatibility names
- **THEN** those names remain available through the facade.
