# Specification

## Requirement: Application Prep Copilot variant application

The system SHALL provide an application-layer use case for applying a selected Prep Copilot variant.

### Scenario: Build application result for selected variant
GIVEN a Prep Copilot variant with a recommendation and readiness report
WHEN the application use case applies the variant
THEN it returns the recommendation, playlist explanation, quality report, readiness report, and variant name.

## Requirement: Desktop delegates Prep Copilot application orchestration

The desktop Prep Copilot controller SHALL delegate selected-variant application business orchestration to the application layer.

### Scenario: Apply delegated selected variant
GIVEN a desktop Prep Copilot controller with an injected variant application builder
WHEN a selected variant is applied
THEN the builder is called with the selected variant
AND the returned application result is stored and rendered by the UI.
