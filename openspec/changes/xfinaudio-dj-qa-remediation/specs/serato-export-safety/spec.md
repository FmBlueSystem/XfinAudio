# Delta for Serato Export Safety

## ADDED Requirements

### Requirement: Blocked Readiness Prevents Silent Export

The system MUST prevent Serato crate writing when DJ readiness is `blocked` unless an explicit override capability is separately specified and tested.

#### Scenario: Export button is disabled for blocked readiness

- GIVEN the latest DJ readiness report status is `blocked`
- WHEN the Export screen renders
- THEN the Serato export action MUST be disabled
- AND guidance MUST explain that blocked readiness checks must be resolved before export.

#### Scenario: Defensive export guard blocks bypassed UI

- GIVEN the latest DJ readiness report status is `blocked`
- WHEN export logic is invoked directly without using the disabled UI button
- THEN the system MUST prevent crate writing
- AND it MUST return or display a clear blocked-export message.

#### Scenario: Preview remains available while blocked

- GIVEN the latest DJ readiness report status is `blocked`
- WHEN the user previews Serato export planning
- THEN preview MUST remain available
- AND preview MUST NOT write files.

### Requirement: Controlled Serato Export Targeting

The system MUST keep automated export validation isolated from the user's real Serato library.

#### Scenario: Controlled E2E export uses temporary Serato folders

- GIVEN automated or scripted QA validates crate writing
- WHEN export is allowed
- THEN the target MUST be a controlled temporary `_Serato_/Subcrates` directory
- AND no automated validation MUST write to the user's real Serato library.

#### Scenario: Destination guidance explains Serato verification

- GIVEN the Export screen is visible
- WHEN destination or history state is shown
- THEN the UI MUST explain the `_Serato_/Subcrates/*.crate` destination format
- AND it SHOULD instruct the user to open Serato and verify crate visibility.
