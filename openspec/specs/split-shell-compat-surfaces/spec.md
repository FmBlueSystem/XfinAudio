# Split Shell Compatibility Surfaces Specification

## ADDED Requirements

### Requirement: Layout compatibility surface is retired after explicit methods
Legacy layout method grafting MUST NOT remain once all former grafted methods exist explicitly on `MainWindow`.

#### Scenario: Layout compatibility module is removed
- **GIVEN** all former layout graft methods are explicit `MainWindow` methods
- **WHEN** the desktop shell imports
- **THEN** it does not import `shell_layout_compat` or call `install_legacy_layout_methods`.

### Requirement: AppState compatibility has its own surface
Legacy MainWindow AppState read/write compatibility MUST live in a state-specific compatibility module.

#### Scenario: State compatibility module owns AppState reads and writes
- **GIVEN** legacy code reads or writes AppState-backed attributes
- **WHEN** `MainWindow` delegates the compatibility operation
- **THEN** the state compatibility module handles it without changing visible behavior.

### Requirement: Shell facade remains stable for state compatibility
Existing state-compatibility imports from `desktop.shell_compat` MUST remain valid while callers migrate to narrower modules.

#### Scenario: Existing facade exports state compatibility names
- **GIVEN** existing tests import `desktop.shell_compat`
- **WHEN** they access legacy state compatibility names
- **THEN** those names remain available through the facade.
