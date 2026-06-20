# Serato Export Application Boundary Specification

## Requirement: Application owns recommendation Serato preview/export
- GIVEN a recommendation and Serato folder WHEN preview is called THEN it returns plan plus selected library and writes nothing.
- GIVEN a recommendation and writer WHEN export is called THEN it builds the plan, calls the writer with `confirm=True`, and returns plan/library/write result.

## Requirement: Desktop remains adapter
- GIVEN an allowed desktop Serato export WHEN the user exports THEN `ExportCoordinator` delegates to the application use case and keeps UI messaging, readiness sidecars, and history rendering.
