# Delta for Export Planning

## ADDED Requirements

### Requirement: Export readiness gate decisions are UI-independent

XfinAudio SHALL determine export readiness through a non-desktop decision boundary before desktop export coordination starts writer-specific planning.

The boundary MUST return a deterministic gate decision for blocked, incomplete, and allowed export requests. Desktop export coordination MUST consume that decision while preserving existing user-visible copy, dialog flow, file planning, Serato planning, and writer output formats.

#### Scenario: Blocked readiness denies export through boundary

- GIVEN export state that is not ready for export
- WHEN export readiness is evaluated
- THEN the non-desktop boundary returns a denied gate decision
- AND desktop export coordination does not invoke file, Serato, or writer planning
- AND desktop-facing blocked-readiness behavior and copy remain unchanged

#### Scenario: Missing recommendation returns desktop-consumed gate decision

- GIVEN no applied recommendation is available for the export request
- WHEN export readiness is evaluated
- THEN the non-desktop boundary returns a denied gate decision for the missing recommendation
- AND desktop export coordination consumes the decision without computing the gate itself
- AND the existing missing-recommendation desktop behavior and copy remain unchanged

#### Scenario: Missing safe folder returns desktop-consumed gate decision

- GIVEN an export request that requires a safe output folder
- AND no safe folder is available
- WHEN export readiness is evaluated
- THEN the non-desktop boundary returns a denied gate decision for the missing safe folder
- AND desktop export coordination consumes the decision without computing the gate itself
- AND the existing safe-folder desktop behavior and copy remain unchanged

#### Scenario: Allowed export continues existing planning

- GIVEN export state that is ready and has required recommendation and folder inputs
- WHEN export readiness is evaluated
- THEN the non-desktop boundary returns an allowed gate decision
- AND desktop export coordination continues to the existing file or Serato planning path
- AND writer formats, target extensions, playlist naming rules, and Serato export behavior remain unchanged
