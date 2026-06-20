# DJ Readiness Summary Application Boundary Specification

## Requirement: Application formats DJ readiness summary text
- GIVEN a DJ readiness report WHEN application summary formatting is requested THEN it returns the same summary text as the existing quality formatter.

## Requirement: Desktop remains adapter
- GIVEN desktop readiness and prep-copilot UI updates WHEN readiness summary text is needed THEN desktop calls the application boundary, not `quality.format_dj_readiness_summary` directly.
