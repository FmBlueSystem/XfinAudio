# Metadata Serato Export Application Boundary Design

Add `xfinaudio.application.serato_metadata_export` with status and missing-field export functions.

The application service selects the Serato library from records, builds the correct metadata worklist plan, and writes through an injectable writer with `confirm=True`.
`ExportCoordinator` keeps user selection and status text but passes its discoverer seam into the application use case.
