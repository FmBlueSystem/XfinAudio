# Specification: AppState track constraints transition boundary

## Requirement: Immutable track constraint transitions

The system SHALL update excluded and locked track constraints through pure AppState transitions instead of direct desktop mutation.

### Scenario: excluding selected tracks is immutable

GIVEN an AppState with existing excluded paths
WHEN selected paths are excluded through the transition
THEN the returned AppState is a new instance
AND selected paths are added to excluded paths
AND the original AppState is unchanged.

### Scenario: locking selected tracks is immutable

GIVEN an AppState with existing locked paths
WHEN selected paths are locked through the transition
THEN the returned AppState is a new instance
AND selected paths are added to locked paths
AND the original AppState is unchanged.

### Scenario: clearing constraints is immutable

GIVEN an AppState with excluded and locked paths
WHEN constraints are cleared through the transition
THEN the returned AppState is a new instance
AND excluded and locked paths are empty
AND the original AppState is unchanged.
