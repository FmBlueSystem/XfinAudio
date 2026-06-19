# Spec: Library repository port boundary

## Requirement 1: Explicit playlist repository contract

The system SHALL expose a playlist repository port describing saved-playlist persistence operations required by desktop/application orchestration.

### Scenario: Coordinator depends on the port

GIVEN playlist coordination code needs saved-playlist persistence
WHEN imports are inspected
THEN the coordinator imports the playlist repository port
AND it does not import the concrete SQLite playlist repository module.

## Requirement 2: Explicit track repository contracts

The system SHALL expose focused track repository ports for scan-result persistence, display listing, and spectral profile cache access without forcing one consumer to depend on every capability.

### Scenario: Workflow uses shared scan persistence port

GIVEN playlist workflow needs to persist scan results
WHEN its repository dependency is typed
THEN it uses the shared track scan persistence port contract
AND does not require display-listing capabilities
AND does not define a duplicate local scan persistence protocol.

## Requirement 3: Concrete repositories remain compatible

The existing SQLite repositories SHALL continue to satisfy the new contracts without changing runtime storage behavior.

### Scenario: Type checker validates concrete adapters

GIVEN the concrete track and playlist repositories
WHEN static type checking runs
THEN the repositories are accepted wherever the new ports are required.
