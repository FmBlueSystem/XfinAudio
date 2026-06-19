# Specification: AppState Prep Copilot variant transition boundary

## Requirement: Immutable Prep Copilot variant application

The system SHALL apply selected Prep Copilot variant state through a pure AppState transition instead of direct desktop mutation.

### Scenario: applying a Prep Copilot variant replaces recommendation context

GIVEN an AppState with stale recommendation fields, removed playlist paths, and an applied variant
WHEN a selected Prep Copilot variant result is applied through the transition
THEN the returned AppState is a new instance
AND recommendation, explanation, quality report, readiness report, and applied variant name reflect the selected variant result
AND removed playlist paths are cleared
AND the original AppState is unchanged.
