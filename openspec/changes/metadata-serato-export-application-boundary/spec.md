# Metadata Serato Export Application Boundary Specification

## Requirement: Application owns metadata Serato worklist exports
- GIVEN metadata records and a status WHEN status export is called THEN it selects the Serato library, plans the filtered worklist crate, writes with `confirm=True`, and returns plan/library/write result.
- GIVEN metadata records and a missing field WHEN missing-field export is called THEN it plans and writes only that missing-field worklist.

## Requirement: Desktop remains adapter
- GIVEN a desktop metadata export WHEN the user exports THEN `ExportCoordinator` delegates planning/writing to application and keeps validation, UI messages, and selected-filter handling.
