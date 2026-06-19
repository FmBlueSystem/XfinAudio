# Specification: Split Shell Compatibility Surfaces

## Requirement: Layout compatibility has its own surface
Legacy layout method grafting MUST live in a layout-specific compatibility module.

### Scenario: Layout compatibility module owns method installation
Given the desktop shell compatibility code
When legacy layout methods are installed on `MainWindow`
Then the layout compatibility module owns the method map and installation behavior.

## Requirement: AppState compatibility has its own surface
Legacy MainWindow AppState read/write compatibility MUST live in a state-specific compatibility module.

### Scenario: State compatibility module owns AppState reads and writes
Given legacy code reads or writes AppState-backed attributes
When `MainWindow` delegates the compatibility operation
Then the state compatibility module handles it without changing visible behavior.

## Requirement: Shell facade remains stable
Existing imports from `desktop.shell_compat` MUST remain valid while callers migrate to narrower modules.

### Scenario: Existing facade exports continue to work
Given existing tests import `desktop.shell_compat`
When they access legacy compatibility names
Then those names remain available through the facade.
