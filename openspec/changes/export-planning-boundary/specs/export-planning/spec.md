# Export Planning Capability

## ADDED Requirements

### Requirement: Playlist file export planning is UI-independent
XfinAudio SHALL compute non-Serato playlist file export names, playlist names, and target paths in a non-UI module.

#### Scenario: Explicit requested name wins
- GIVEN a Traktor export request with requested name `Warmup`
- AND an applied variant name `balanced`
- WHEN the export plan is built
- THEN the plan target name is `Warmup`
- AND the plan playlist name is `Warmup`
- AND the target path is `<safe folder>/Warmup.nml`

#### Scenario: Variant name wins when requested name is absent
- GIVEN a Rekordbox export request without requested name
- AND an applied variant name `Balanced Variant`
- WHEN the export plan is built
- THEN the plan target name is `Balanced Variant`
- AND the target path is `<safe folder>/Balanced Variant.xml`

#### Scenario: Generated name uses software suffix
- GIVEN a VirtualDJ export request without requested name or variant name
- WHEN the export plan is built at a fixed timestamp
- THEN the generated target name includes the sanitized `virtualdj` suffix
- AND the target path uses `.xml`

#### Scenario: Unknown software is rejected
- GIVEN an unsupported playlist file export software name
- WHEN the export plan is built
- THEN the planner raises a deterministic error naming the unsupported software
