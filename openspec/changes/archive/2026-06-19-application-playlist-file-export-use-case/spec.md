# Spec: Application Playlist File Export Use Case

## Requirement: Non-Serato playlist file export is orchestrated by Application layer

The system MUST orchestrate non-Serato playlist file export planning and writer dispatch outside the desktop UI layer.

### Scenario: Preview returns a deterministic export plan

- GIVEN a recommendation, selected non-Serato software, safe folder, optional requested name, optional variant name, and optional timestamp
- WHEN preview is requested
- THEN the use case MUST return the same deterministic export plan used by the desktop preview
- AND it MUST NOT write any file.

### Scenario: Export writes through the selected writer

- GIVEN a recommendation and supported non-Serato software
- WHEN export is requested
- THEN the use case MUST build the export plan
- AND call the writer registered for that software
- AND return the written path.

### Scenario: Unknown software remains rejected

- GIVEN an unsupported software name
- WHEN preview or export is requested
- THEN the use case MUST raise a value error compatible with the existing desktop error behavior.
