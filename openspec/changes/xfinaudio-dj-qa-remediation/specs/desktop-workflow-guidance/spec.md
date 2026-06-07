# Delta for Desktop Workflow Guidance

## ADDED Requirements

### Requirement: Build Playlist Explains Recommendation Value

The Build Playlist screen MUST explain the selected anchor, active strategy, available constraints, and difference between deterministic recommendation and Prep Copilot.

#### Scenario: Anchor summary is visible before recommendation

- GIVEN a library track is selected as the anchor
- WHEN the Build Playlist screen renders
- THEN the screen MUST show title, artist, BPM, key, and energy for the selected anchor when available.

#### Scenario: Strategy explanation is visible

- GIVEN a strategy is selected
- WHEN the Build Playlist screen renders
- THEN the screen MUST explain what the strategy does in user-facing language.

#### Scenario: Recommendation and Prep Copilot are distinguished

- GIVEN the Build Playlist screen shows both recommendation and Prep Copilot actions
- WHEN the user reads the screen guidance
- THEN the guidance MUST explain that recommendation builds one deterministic sequence
- AND Prep Copilot compares alternatives before the DJ chooses.

#### Scenario: Variant actions are unavailable until variants exist

- GIVEN no Prep Copilot variants have been generated
- WHEN the Build Playlist screen renders
- THEN variant apply controls MUST be disabled or hidden
- AND the empty state MUST explain how to generate variants.

### Requirement: Build Playlist Shows Recommendation Summary

The Build Playlist screen MUST show a concise recommendation summary after generation without duplicating the full Review Mix screen.

#### Scenario: Generated recommendation summary appears

- GIVEN a recommendation has been generated
- WHEN the Build Playlist screen renders
- THEN it MUST show track count, first few tracks, warning count, and a call to review mix details before export.

### Requirement: Review Mix Leads With DJ Decision

The Review Mix screen MUST translate scores and readiness into a clear DJ decision before detailed tables.

#### Scenario: Ready recommendation leads with export decision

- GIVEN readiness has no blockers and warnings are acceptable
- WHEN the Review Mix screen renders
- THEN the first visible decision message MUST say the mix is ready to export.

#### Scenario: Warning recommendation leads with review decision

- GIVEN readiness has warnings but is not blocked
- WHEN the Review Mix screen renders
- THEN the first visible decision message MUST say the mix needs review before export.

#### Scenario: Blocked recommendation leads with no-export decision

- GIVEN readiness is blocked
- WHEN the Review Mix screen renders
- THEN the first visible decision message MUST say not to export yet.

### Requirement: Empty States Teach Workflow

Export and Metadata screens MUST use meaningful empty-state guidance instead of placeholder symbols.

#### Scenario: Export empty state explains purpose

- GIVEN no export history exists
- WHEN the Export screen renders
- THEN it MUST explain what will be exported, where it lands, and that preview does not write files.

#### Scenario: Metadata worklist empty state explains repair loop

- GIVEN no metadata worklist has been generated or no missing metadata is selected
- WHEN the Metadata screen renders
- THEN it MUST explain the repair loop: fix BPM/key/energy externally, then refresh XfinAudio.
