# Specification

## Requirement: Application DJ readiness use case

The system SHALL provide an application-layer use case for building a DJ readiness report from a playlist recommendation, quality report, and optional Serato export context.

### Scenario: Build readiness through application layer
GIVEN a playlist recommendation and its quality report
WHEN the DJ readiness application use case is called
THEN it returns the same operational readiness report produced by the domain quality rules.

### Scenario: Preserve optional Serato context
GIVEN a playlist recommendation, quality report, Serato export plan, and volume root
WHEN the DJ readiness application use case is called
THEN the optional Serato validation context is passed through to readiness evaluation.

## Requirement: Desktop controller delegates business orchestration

The desktop DJ readiness controller SHALL receive a readiness builder dependency and use it to obtain the report before rendering.

### Scenario: Render delegated readiness report
GIVEN a desktop DJ readiness controller with an injected readiness builder
WHEN the controller shows DJ readiness for a recommendation
THEN the injected builder is called with the recommendation, quality report, and optional Serato context
AND the returned report is stored, summarized, and rendered in the readiness table.
