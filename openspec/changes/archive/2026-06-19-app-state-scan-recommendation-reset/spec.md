# Specification: AppState scan recommendation reset boundary

## Requirement: Immutable scan-dependent recommendation reset

When scan-dependent state is cleared, the system SHALL clear recommendation-derived state through a pure AppState transition instead of direct UI/controller mutation.

### Scenario: clearing scan-dependent state resets recommendation context

GIVEN an AppState with scanned records, records-by-path, recommendation, explanation, quality report, readiness report, removed playlist paths, and applied Prep Copilot variant
WHEN scan-dependent state is cleared through the transition
THEN the returned AppState is a new instance
AND scan records and records-by-path are cleared
AND recommendation-derived state is cleared
AND the original AppState is unchanged.

### Scenario: unrelated constraints are preserved

GIVEN an AppState with excluded and locked track constraints
WHEN scan-dependent state is cleared through the transition
THEN excluded and locked track constraints remain unchanged.
