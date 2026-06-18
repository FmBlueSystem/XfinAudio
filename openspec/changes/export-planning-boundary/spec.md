# Export Planning Boundary Spec

## Requirement: Plan playlist file exports outside desktop UI

### Scenario: Explicit requested name wins
GIVEN a non-Serato export request with software `Traktor`
AND a requested name `Warmup`
AND an applied variant name `balanced`
WHEN the planner builds the file export plan
THEN the target name and playlist name are `Warmup`
AND the target path ends in `Warmup.nml`.

### Scenario: Variant name wins when requested name is absent
GIVEN a non-Serato export request with software `Rekordbox`
AND no requested name
AND an applied variant name `Balanced Variant`
WHEN the planner builds the file export plan
THEN the target name and playlist name are `Balanced Variant`
AND the target path ends in `Balanced Variant.xml`.

### Scenario: Generated name uses software suffix
GIVEN a non-Serato export request with software `VirtualDJ`
AND no requested name
AND no applied variant name
WHEN the planner builds the file export plan at a fixed timestamp
THEN the generated target name includes the sanitized `virtualdj` suffix
AND the target path has an `.xml` extension.

### Scenario: Unknown software is rejected
GIVEN a non-Serato export request with unsupported software
WHEN the planner builds the file export plan
THEN it raises `ValueError` with the unknown software name.
