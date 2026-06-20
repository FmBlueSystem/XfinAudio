# DJ Readiness Export Application Boundary Specification

## Requirement: Application writes DJ readiness reports
- GIVEN a DJ readiness report and target JSON/CSV paths WHEN the application export boundary is called THEN it writes through the existing quality writer and returns the written paths.

## Requirement: Desktop remains adapter
- GIVEN desktop export actions/coordinator WHEN DJ readiness sidecars are exported THEN desktop calls the application boundary, not `quality.write_dj_readiness_report` directly.
