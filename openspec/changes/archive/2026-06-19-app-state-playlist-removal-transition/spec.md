# Specification: AppState playlist removal transition boundary

## Requirement: Immutable playlist removal transitions

The system SHALL update removed playlist paths through pure AppState transitions instead of direct desktop mutation.

### Scenario: removing a playlist path is immutable

GIVEN an AppState with existing removed playlist paths
WHEN a playlist path is removed through the transition
THEN the returned AppState is a new instance
AND the path is included in removed playlist paths
AND existing removed paths are preserved
AND the original AppState is unchanged.

### Scenario: restoring a playlist path is immutable

GIVEN an AppState with a removed playlist path
WHEN the playlist path is restored through the transition
THEN the returned AppState is a new instance
AND the path is absent from removed playlist paths
AND unrelated removed paths are preserved
AND the original AppState is unchanged.
