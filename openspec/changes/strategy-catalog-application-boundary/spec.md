# Strategy Catalog Application Boundary Specification

## Requirement: Application exposes strategy display catalog
- GIVEN built-in recommendation strategies WHEN desktop asks for display options THEN application returns ordered public strategy summaries.
- GIVEN a strategy name WHEN desktop asks for an explanation THEN application returns its description or an empty fallback for unknown input.

## Requirement: Desktop remains adapter
- GIVEN BuildViewModel rendering WHEN strategies are needed THEN desktop reads the application catalog, not private recommendation internals.
