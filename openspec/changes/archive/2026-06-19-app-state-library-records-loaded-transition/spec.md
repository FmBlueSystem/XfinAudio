# Spec: App State Library Records Loaded Transition

## Requirement: Library records load through a pure AppState transition

The system MUST store loaded library records and rebuild their lookup map through a pure AppState transition.

### Scenario: Loaded records update state immutably

- GIVEN AppState has existing scanned records and a record lookup map
- WHEN library records are loaded
- THEN the transition MUST return a new AppState instance
- AND `scanned_records` MUST contain the loaded records
- AND `records_by_path` MUST be rebuilt from those records
- AND the original AppState MUST remain unchanged.

### Scenario: Controller keeps table rendering responsibility

- GIVEN records are displayed in the desktop library table
- WHEN the table is populated
- THEN table rendering and filtering MUST remain desktop responsibilities
- AND loaded-record state policy MUST remain delegated to the pure transition helper.
