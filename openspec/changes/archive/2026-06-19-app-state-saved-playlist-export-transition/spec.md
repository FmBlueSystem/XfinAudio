# Specification: AppState saved playlist export transition boundary

## Requirement: Immutable saved playlist export recommendation transition

The system SHALL replace the current recommendation for saved-playlist export through a pure AppState transition instead of direct desktop mutation.

### Scenario: saved playlist export recommendation replacement is immutable

GIVEN an AppState with a previous recommendation
WHEN a saved playlist export recommendation is applied through the transition
THEN the returned AppState is a new instance
AND the last recommendation reflects the saved playlist recommendation
AND the original AppState is unchanged.
