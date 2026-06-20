# Recommendation Candidate Application Boundary Specification

## Requirement: Application plans desktop recommendation candidates
- GIVEN scanned records and optional DJ controls WHEN desktop needs an interactive recommendation pool THEN application returns the same ordered candidate records as the existing recommendation policy.
- GIVEN manual/start/end/locked control tracks WHEN application plans the pool THEN control tracks remain prioritized and duplicate priorities are collapsed.

## Requirement: Desktop remains adapter
- GIVEN `MainWindow` builds desktop recommendation records WHEN it delegates candidate planning THEN it calls the application boundary instead of importing recommendation candidate-pool internals.
