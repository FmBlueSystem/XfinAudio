# MainWindow State Compatibility Boundary Specification

## ADDED Requirements

### Requirement: Explicit legacy state write compatibility
`MainWindow` MUST delegate AppState-backed legacy attribute writes to an explicit desktop shell compatibility boundary instead of owning the write policy inline.

#### Scenario: AppState-backed write is handled by the compatibility helper
- **GIVEN** a `MainWindow` instance with initialized AppState
- **WHEN** legacy code assigns an AppState-backed attribute
- **THEN** the compatibility helper handles the assignment
- **AND** the corresponding AppState value is updated without changing visible UI behavior.

### Requirement: Non-state writes remain normal Qt/object writes
`MainWindow` MUST preserve normal attribute assignment for names outside the AppState compatibility set.

#### Scenario: Non-state attribute write bypasses compatibility handling
- **GIVEN** a `MainWindow` instance
- **WHEN** code assigns a non-AppState-backed attribute
- **THEN** assignment proceeds through normal object behavior.

### Requirement: Service mirrors remain synchronized
Legacy writes that also mirror state into scan or recommendation services MUST keep the current synchronization behavior.

#### Scenario: Workflow service write updates dependent services
- **GIVEN** a `MainWindow` instance with scan and recommendation services
- **WHEN** legacy code assigns `workflow_service`
- **THEN** AppState, scan service, and recommendation service all reference the assigned workflow service.
