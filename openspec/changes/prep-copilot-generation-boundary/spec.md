# Prep Copilot Generation Application Boundary Specification

## Requirement: Application owns Prep Copilot generation
- GIVEN records and UI-derived generation parameters WHEN the application use case is called THEN it builds the `DJSetIntent`, delegates to the planner, and returns the generated plan.

## Requirement: Desktop remains adapter
- GIVEN valid selected controls WHEN the user generates Prep Copilot variants THEN desktop delegates generation to the application use case and only updates state/widgets/status from the returned plan.
