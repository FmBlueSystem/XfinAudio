# Specification: AppState Prep Copilot plan transition boundary

## Requirement: Immutable Prep Copilot plan transitions

The system SHALL store and clear Prep Copilot plans through pure AppState transitions instead of direct desktop mutation.

### Scenario: storing a Prep Copilot plan is immutable

GIVEN an AppState without a plan
WHEN a Prep Copilot plan is stored through the transition
THEN the returned AppState is a new instance
AND the plan is stored
AND the original AppState is unchanged.

### Scenario: clearing a Prep Copilot plan is immutable

GIVEN an AppState with a plan
WHEN the plan is cleared through the transition
THEN the returned AppState is a new instance
AND the plan is cleared
AND the original AppState is unchanged.
